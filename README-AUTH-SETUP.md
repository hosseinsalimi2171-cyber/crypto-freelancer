# CryptoEngineer Auth & Site Inbox Setup

This GitHub Pages build uses Supabase for authentication and the database.

## 1. Create a Supabase project
Create a project at https://supabase.com/ and copy the Project URL and Publishable/anon key.

## 2. Configure the site
Open `config.js` and replace:
- `YOUR_PROJECT.supabase.co`
- `YOUR_PUBLISHABLE_OR_ANON_KEY`

Do **not** put a `service_role` key in the website.

## 3. Create the database
Open the Supabase SQL Editor and run all SQL in `supabase-schema.sql`.

## 4. Configure Auth
Enable email/password sign-up in Supabase Authentication. If email confirmation is enabled, users must confirm their email before signing in.

## 5. Make your own account the administrator
After creating your account, run the final UPDATE statement in `supabase-schema.sql` with your account email. This gives you access to `requests.html` and the request counter on the home page.

## Features
- Email/password Sign Up and Sign In
- Persistent sessions in the browser
- Authenticated project submissions
- Project submissions stored as pending until reviewed
- Hire/project requests stored in the database instead of email
- Admin request inbox with request count
- Admin can mark requests Reviewing or Closed

GitHub Pages remains the static frontend; Supabase supplies authentication and database functionality.
