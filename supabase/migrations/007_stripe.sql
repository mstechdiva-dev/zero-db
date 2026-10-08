-- Migration 007: Stripe billing
-- Billing moves from Lemon Squeezy to Stripe. Renames the customer and
-- subscription columns to stripe_* and drops the portal URL column (Stripe
-- creates portal links on demand). Safe to run again, and safe on a database
-- that never had the Lemon Squeezy columns.

do $$
begin
  if exists (select 1 from information_schema.columns
             where table_name = 'organizations' and column_name = 'lemonsqueezy_customer_id') then
    if exists (select 1 from information_schema.columns
               where table_name = 'organizations' and column_name = 'stripe_customer_id') then
      -- both exist: keep any value already on the old column, then drop it
      update organizations set stripe_customer_id = coalesce(stripe_customer_id, lemonsqueezy_customer_id);
      alter table organizations drop column lemonsqueezy_customer_id;
    else
      alter table organizations rename column lemonsqueezy_customer_id to stripe_customer_id;
    end if;
  end if;

  if exists (select 1 from information_schema.columns
             where table_name = 'organizations' and column_name = 'lemonsqueezy_subscription_id') then
    if exists (select 1 from information_schema.columns
               where table_name = 'organizations' and column_name = 'stripe_subscription_id') then
      update organizations set stripe_subscription_id = coalesce(stripe_subscription_id, lemonsqueezy_subscription_id);
      alter table organizations drop column lemonsqueezy_subscription_id;
    else
      alter table organizations rename column lemonsqueezy_subscription_id to stripe_subscription_id;
    end if;
  end if;
end $$;

alter table organizations add column if not exists stripe_customer_id text;
alter table organizations add column if not exists stripe_subscription_id text;
alter table organizations drop column if exists lemonsqueezy_customer_portal_url;
