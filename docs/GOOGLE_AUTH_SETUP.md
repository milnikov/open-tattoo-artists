# Google Auth (Sign in with Google)

Order: **Google Cloud** → **Supabase** → **app env** → optional **SQL schema**.

## 1. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) — create or select a project.  
2. **APIs & Services → OAuth consent screen** — External (or Internal for workspace). App name, support + developer emails. **Scopes:** include `openid` (required for Supabase); profile/email are usually added by default.  
3. **APIs & Services → Credentials → OAuth client ID** — Type **Web application**.  
   - **Authorized JavaScript origins:** `http://localhost:3000` (dev) and `https://your-domain.com` (prod).  
   - **Authorized redirect URIs:** **`https://<PROJECT-REF>.supabase.co/auth/v1/callback`** only (not your app URL). Ref: Supabase → Project Settings → General.  
   - Save **Client ID** and **Client Secret**.

## 2. Supabase

1. **Authentication → Providers → Google** — enable, paste Client ID + Secret.  
2. **Authentication → URL Configuration** — **Site URL** = prod or `http://localhost:3000`. **Redirect URLs** include `http://localhost:3000/auth/callback` and `https://your-domain.com/auth/callback`.

## 3. App (`apps/web/.env.local`)

```env
NEXT_PUBLIC_SUPABASE_URL=https://<PROJECT-REF>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon public key>
```

Keys: **Project Settings → API**.

## 4. Database

If needed: **SQL Editor** — run `supabase/schema.sql` (`profiles`, `favourites`, RLS).

## 5. Run

`cd apps/web && npm run dev` — test **Sign in with Google** from `/profile`.

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| Redirect URI mismatch (Google) | Redirect in Google must be exactly `https://<ref>.supabase.co/auth/v1/callback`. |
| Redirect URL not allowed (Supabase) | Add `/auth/callback` URLs under **Authentication → URL Configuration**. |
| Session not sticking | Callback route reachable; HTTPS in prod; cookies not blocked. |
