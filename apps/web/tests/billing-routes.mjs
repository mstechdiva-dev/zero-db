// Billing route checks: runs the BUILT website against a fake Stripe and a fake Supabase, then sends
// signed Stripe events and checkout/portal requests. No real accounts, keys or money involved.
//
//   npm run build        (any dummy NEXT_PUBLIC_SUPABASE_* / SUPABASE_SERVICE_ROLE_KEY values will do)
//   npm run test:billing
import http from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import Stripe from 'stripe';

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const results = []; const check = (name, ok, extra='') => { results.push(ok); console.log((ok?'PASS ':'FAIL ')+name+(ok?'':'  '+extra)); };

// ---- fake Supabase (auth + a little PostgREST) ----
const db = { users: [{ auth_user_id: 'user-1', org_id: 'org-1' }],
  organizations: [{ id: 'org-1', plan: 'trial', trial_converted: false, trial_ends_at: '2099-01-01T00:00:00Z',
                    stripe_customer_id: null, stripe_subscription_id: null }] };
let failWrites = false, failReads = false;
const parseFilters = (u) => [...u.searchParams].filter(([k]) => k !== 'select').map(([k, v]) => [k, v.replace(/^eq\./, '')]);
const supa = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x'); let body = '';
  req.on('data', c => body += c); req.on('end', () => {
    const send = (code, obj) => { res.writeHead(code, {'content-type':'application/json'}); res.end(obj === undefined ? '' : JSON.stringify(obj)); };
    if (u.pathname === '/auth/v1/user') return send(200, { id: 'user-1', email: 'u@example.com', aud: 'authenticated', app_metadata: {}, user_metadata: {}, created_at: '2026-01-01T00:00:00Z' });
    const m = u.pathname.match(/^\/rest\/v1\/(\w+)$/); if (!m) return send(404, {});
    const rows = db[m[1]]; const f = parseFilters(u);
    const match = rows.filter(r => f.every(([k, v]) => String(r[k]) === v));
    if (req.method === 'GET') {
      if (failReads && m[1] === 'organizations') return send(500, { message: 'db read failed' });
      if ((req.headers.accept || '').includes('pgrst.object')) return match.length ? send(200, match[0]) : send(406, { code: 'PGRST116', message: 'no rows' });
      return send(200, match);
    }
    if (req.method === 'PATCH') { if (failWrites) return send(500, { message: 'db down' }); match.forEach(r => Object.assign(r, JSON.parse(body))); return send(204); }
    send(405, {});
  });
});

// ---- fake Stripe ----
const stripeCalls = []; let stripeFail = false;
const fakeStripe = http.createServer((req, res) => {
  let body = ''; req.on('data', c => body += c); req.on('end', () => {
    stripeCalls.push({ path: req.url, form: Object.fromEntries(new URLSearchParams(body)), idem: req.headers['idempotency-key'] });
    if (stripeFail) { res.writeHead(400, {'content-type':'application/json'}); return res.end(JSON.stringify({ error: { type: 'invalid_request_error', message: 'No such price: price_secret_detail' } })); }
    res.writeHead(200, {'content-type':'application/json'});
    res.end(JSON.stringify({ id: 'cs_test_1', object: 'checkout.session', url: req.url.includes('portal') ? 'https://billing.stripe.test/p/abc' : 'https://checkout.stripe.test/c/abc' }));
  });
});

const sessionCookie = () => {
  const b64 = s => Buffer.from(s).toString('base64url');
  const jwt = [b64('{"alg":"HS256","typ":"JWT"}'), b64(JSON.stringify({ sub: 'user-1', exp: 4102444800, aud: 'authenticated', role: 'authenticated' })), 'sig'].join('.');
  const session = { access_token: jwt, refresh_token: 'r', token_type: 'bearer', expires_in: 3600, expires_at: 4102444800,
    user: { id: 'user-1', email: 'u@example.com', aud: 'authenticated', app_metadata: {}, user_metadata: {}, created_at: '2026-01-01T00:00:00Z' } };
  return 'sb-127-auth-token=base64-' + b64(JSON.stringify(session));
};

const WH = 'whsec_test_123';
const signer = new Stripe('sk_test_x');
const post = (port, path, { body = '', headers = {} } = {}) => new Promise(resolve => {
  const r = http.request({ host: '127.0.0.1', port, path, method: 'POST', headers: { 'content-type': 'application/json', ...headers } }, res => {
    let d = ''; res.on('data', c => d += c); res.on('end', () => { let j; try { j = JSON.parse(d); } catch { j = d; } resolve({ status: res.statusCode, json: j }); });
  }); r.end(body);
});
const hook = (port, evt, { sign = true } = {}) => {
  const payload = JSON.stringify(evt);
  const header = sign ? signer.webhooks.generateTestHeaderString({ payload, secret: WH }) : 'bad';
  return post(port, '/api/webhook/stripe', { body: payload, headers: { 'stripe-signature': header } });
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const org = () => db.organizations[0];

(async () => {
  await new Promise(r => supa.listen(8802, r)); await new Promise(r => fakeStripe.listen(8801, r));
  const base = { ...process.env, NEXT_PUBLIC_SUPABASE_URL: 'http://127.0.0.1:8802', NEXT_PUBLIC_SUPABASE_ANON_KEY: 'anon', SUPABASE_SERVICE_ROLE_KEY: 'svc' };
  const configured = spawn('npx', ['next', 'start', '-p', '3201'], { cwd: webDir, env: { ...base, STRIPE_SECRET_KEY: 'sk_test_x', STRIPE_WEBHOOK_SECRET: WH, STRIPE_PRICE_ID_SOLO: 'price_test', STRIPE_API_BASE_URL: 'http://127.0.0.1:8801' }, stdio: 'ignore' });
  const bare = spawn('npx', ['next', 'start', '-p', '3202'], { cwd: webDir, env: base, stdio: 'ignore' });
  await sleep(6000);
  try {
    // ---------- webhook ----------
    const done = (obj) => ({ type: 'checkout.session.completed', data: { object: obj } });
    const session = { id: 'cs_1', object: 'checkout.session', mode: 'subscription', payment_status: 'paid', client_reference_id: 'org-1', customer: 'cus_1', subscription: 'sub_1' };
    let r = await hook(3201, done(session), { sign: false });
    check('webhook: bad signature rejected (400)', r.status === 400 && org().plan === 'trial', JSON.stringify(r));
    r = await hook(3201, done(session));
    check('webhook: paid checkout puts the org on Solo', r.status === 200 && org().plan === 'solo' && org().trial_converted === true && org().stripe_customer_id === 'cus_1' && org().stripe_subscription_id === 'sub_1', JSON.stringify(org()));
    r = await hook(3201, { type: 'customer.subscription.updated', data: { object: { id: 'sub_1', object: 'subscription', status: 'past_due', customer: 'cus_1', metadata: { org_id: 'org-1' } } } });
    check('webhook: past_due leaves the plan alone', r.status === 200 && org().plan === 'solo');
    r = await hook(3201, { type: 'customer.subscription.deleted', data: { object: { id: 'sub_OLD', object: 'subscription', status: 'canceled', customer: 'cus_1', metadata: { org_id: 'org-1' } } } });
    check('webhook: cancelling an OLD subscription does not undo the current one', r.status === 200 && org().plan === 'solo' && org().stripe_subscription_id === 'sub_1');
    r = await hook(3201, { type: 'customer.subscription.deleted', data: { object: { id: 'sub_1', object: 'subscription', status: 'canceled', customer: 'cus_1', metadata: { org_id: 'org-1' } } } });
    check('webhook: cancelling the current subscription ends access', r.status === 200 && org().plan === 'trial' && org().trial_converted === false && org().stripe_subscription_id === null && org().stripe_customer_id === 'cus_1' && new Date(org().trial_ends_at) <= new Date(), JSON.stringify(org()));
    r = await hook(3201, { type: 'customer.subscription.updated', data: { object: { id: 'sub_2', object: 'subscription', status: 'active', customer: 'cus_1', metadata: { org_id: 'org-1' } } } });
    check('webhook: resubscribing (active) restores Solo', r.status === 200 && org().plan === 'solo' && org().stripe_subscription_id === 'sub_2');
    r = await hook(3201, { type: 'customer.subscription.updated', data: { object: { id: 'sub_2', object: 'subscription', status: 'canceled', customer: 'cus_1', metadata: {} } } });
    check('webhook: finds the org by subscription id when metadata is missing', r.status === 200 && org().plan === 'trial' && org().stripe_subscription_id === null, JSON.stringify(org()));
    r = await hook(3201, { type: 'invoice.paid', data: { object: { id: 'in_1', object: 'invoice' } } });
    check('webhook: unrelated events are acknowledged', r.status === 200 && r.json.received === true);
    failWrites = true; r = await hook(3201, done(session)); failWrites = false;
    check('webhook: a database failure returns 500 so Stripe retries', r.status === 500, JSON.stringify(r));

    // a failed fallback lookup must return 500 (so Stripe retries), not a quiet 200
    org().plan = 'solo'; org().stripe_subscription_id = 'sub_9'; org().trial_converted = true;
    failReads = true;
    r = await hook(3201, { type: 'customer.subscription.updated', data: { object: { id: 'sub_9', object: 'subscription', status: 'canceled', customer: 'cus_1', metadata: {} } } });
    failReads = false;
    check('webhook: a failed org lookup returns 500 so Stripe retries', r.status === 500 && org().plan === 'solo', JSON.stringify([r, org()]));

    // ---------- checkout ----------
    org().plan = 'trial'; org().trial_converted = false; org().stripe_customer_id = null; org().stripe_subscription_id = null;
    r = await post(3201, '/api/checkout');
    check('checkout: signed-out request is refused (401)', r.status === 401, JSON.stringify(r));
    stripeCalls.length = 0; r = await post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } });
    const c1 = stripeCalls[0] && stripeCalls[0].form;
    check('checkout: returns the Stripe URL', r.status === 200 && r.json.url === 'https://checkout.stripe.test/c/abc', JSON.stringify(r));
    check('checkout: sends a Solo subscription tied to the org', c1 && stripeCalls[0].path === '/v1/checkout/sessions' && c1.mode === 'subscription' && c1['line_items[0][price]'] === 'price_test' && c1['line_items[0][quantity]'] === '1' && c1.client_reference_id === 'org-1' && c1.customer_email === 'u@example.com' && c1['subscription_data[metadata][org_id]'] === 'org-1' && !c1.customer, JSON.stringify(c1));
    check('checkout: return links come back to Settings', c1 && c1.success_url === 'http://localhost:3201/dashboard/settings?billing=success' && c1.cancel_url === 'http://localhost:3201/dashboard/settings?billing=cancelled', JSON.stringify(c1 && [c1.success_url, c1.cancel_url]));
    org().stripe_customer_id = 'cus_9'; stripeCalls.length = 0; r = await post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } });
    const c2 = stripeCalls[0] && stripeCalls[0].form;
    check('checkout: reuses the existing Stripe customer', r.status === 200 && c2 && c2.customer === 'cus_9' && !c2.customer_email, JSON.stringify(c2));
    org().plan = 'solo'; org().stripe_subscription_id = 'sub_1'; stripeCalls.length = 0; r = await post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } });
    check('checkout: already-subscribed orgs get 409 and Stripe is not called', r.status === 409 && stripeCalls.length === 0, JSON.stringify(r));
    org().plan = 'trial'; org().stripe_subscription_id = null; stripeFail = true; r = await post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } }); stripeFail = false;
    check('checkout: a Stripe error gives a safe 502 message', r.status === 502 && !JSON.stringify(r.json).includes('price_secret_detail'), JSON.stringify(r));

    // two checkouts for the same org at once must share one Stripe session key
    org().plan = 'trial'; org().stripe_customer_id = null; org().stripe_subscription_id = null; stripeCalls.length = 0;
    await Promise.all([post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } }), post(3201, '/api/checkout', { headers: { cookie: sessionCookie() } })]);
    check('checkout: two requests at once send the SAME idempotency key (no duplicate subscriptions)', stripeCalls.length === 2 && stripeCalls[0].idem && stripeCalls[0].idem === stripeCalls[1].idem && stripeCalls[0].idem.startsWith('checkout-org-1-'), JSON.stringify(stripeCalls.map(c => c.idem)));

    // ---------- portal ----------
    org().stripe_customer_id = null; r = await post(3201, '/api/billing/portal', { headers: { cookie: sessionCookie() } });
    check('portal: no billing account gives 400', r.status === 400, JSON.stringify(r));
    r = await post(3201, '/api/billing/portal'); check('portal: signed-out request is refused (401)', r.status === 401);
    org().stripe_customer_id = 'cus_9'; stripeCalls.length = 0; r = await post(3201, '/api/billing/portal', { headers: { cookie: sessionCookie() } });
    const p1 = stripeCalls[0] && stripeCalls[0].form;
    check('portal: opens the Stripe portal for the org\'s customer', r.status === 200 && r.json.url === 'https://billing.stripe.test/p/abc' && p1.customer === 'cus_9' && p1.return_url === 'http://localhost:3201/dashboard/settings', JSON.stringify([r, p1]));

    // ---------- not configured ----------
    const a = await post(3202, '/api/checkout', { headers: { cookie: sessionCookie() } });
    const b = await post(3202, '/api/billing/portal', { headers: { cookie: sessionCookie() } });
    const w = await post(3202, '/api/webhook/stripe', { body: '{}', headers: { 'stripe-signature': 'x' } });
    check('unconfigured: checkout, portal and webhook all say billing isn\'t set up (503)', a.status === 503 && b.status === 503 && w.status === 503, JSON.stringify([a.status, b.status, w.status]));
  } finally {
    configured.kill(); bare.kill(); supa.close(); fakeStripe.close();
  }
  const bad = results.filter(x => !x).length;
  console.log(`\n${results.length - bad}/${results.length} passed`); process.exit(bad ? 1 : 0);
})();
