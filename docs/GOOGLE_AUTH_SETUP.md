# Google Auth Setup

To make **Sign in with Google** available in the app, complete these steps in order.

## 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. **APIs & Services → OAuth consent screen**
   - Choose **External** (or Internal for workspace-only).
   - Fill **App name**, **User support email**, **Developer contact**.
   - **Scopes**: add `openid` (Supabase needs it). `.../auth/userinfo.profile` and `.../auth/userinfo.email` are usually already there.
   - Save.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**.
   - **Authorized JavaScript origins**
     - Local: `http://localhost:3000` (or your dev port).
     - Production: `https://your-domain.com`.
   - **Authorized redirect URIs**
     - Use your **Supabase** auth callback, not your app URL:
     - `https://<YOUR-PROJECT-REF>.supabase.co/auth/v1/callback`
     - Project ref is in Supabase Dashboard → Project Settings → General → Reference ID.
   - Create and copy **Client ID** and **Client Secret**.

## 2. Supabase Dashboard

1. Open your project: [Supabase Dashboard](https://supabase.com/dashboard) → your project.
2. **Authentication → Providers → Google**
   - Enable **Google**.
   - Paste **Client ID** and **Client Secret** from step 1.
   - Save.
3. **Authentication → URL Configuration**
   - **Site URL**: production URL (e.g. `https://your-domain.com`) or `http://localhost:3000` for local.
   - **Redirect URLs**: add:
     - `http://localhost:3000/auth/callback` (dev)
     - `https://your-domain.com/auth/callback` (prod)
   - Save.

## 3. App environment

In `apps/web/.env.local` (create from `.env.example`):

```env
NEXT_PUBLIC_SUPABASE_URL=https://<YOUR-PROJECT-REF>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
```

Anon key: Supabase Dashboard → Project Settings → API → Project API keys → `anon` public.

## 4. Apply database schema (if not done)

In Supabase: **SQL Editor** → run the contents of `supabase/schema.sql` so tables (`profiles`, `favourites`, etc.) and RLS exist.

## 5. Run the app

```bash
cd apps/web && npm run dev
```

Open `/profile` and use **Sign in with Google**. After authorizing, you are redirected back and the session is stored.

## Troubleshooting

- **Redirect URI mismatch**: Redirect URI in Google must be exactly `https://<ref>.supabase.co/auth/v1/callback` (your Supabase project ref).
- **Redirect URL not allowed**: Add `http://localhost:3000/auth/callback` (and your production callback URL) under Supabase → Authentication → URL Configuration → Redirect URLs.
- **Session not persisting**: Ensure the auth callback route is reachable and that cookies are not blocked (same-site, HTTPS in production).
