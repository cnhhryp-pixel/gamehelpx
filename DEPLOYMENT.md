# GameHelpX Production Deployment

GameHelpX is designed for static deployment through GitHub → Cloudflare Pages.

## Cloudflare Pages project

- Repository: `cnhhryp-pixel/gamehelpx`
- Production branch: `main`
- Framework preset: None
- Build command: leave empty
- Build output directory: `/` (repository root)
- Root directory: leave empty
- Node/package install step: not required

## Production domains

Primary canonical domain:

- `https://gamehelpx.com`

Optional secondary domain:

- `https://www.gamehelpx.com`

The repository redirects `www.gamehelpx.com/*` to the apex domain.

## After connecting the domain

Verify:

- `https://gamehelpx.com/`
- `https://gamehelpx.com/robots.txt`
- `https://gamehelpx.com/sitemap.xml`
- `https://gamehelpx.com/tools/`
- `https://gamehelpx.com/games/elden-ring/`

Expected production behavior:

- `robots.txt` points to `https://gamehelpx.com/sitemap.xml`
- canonicals use `https://gamehelpx.com/`
- `_headers` provides security/cache headers
- `_redirects` provides canonical redirects
- `404.html` is the custom not-found page

## Search Console

After the production domain resolves:

1. Verify `gamehelpx.com` in Google Search Console.
2. Submit `https://gamehelpx.com/sitemap.xml`.
3. Inspect the homepage and several high-value hubs/tools.
4. Request indexing only after production URLs return successfully.

## Development preview

GitHub Pages remains the development preview:

- `https://cnhhryp-pixel.github.io/gamehelpx/`

Do not use the GitHub Pages URL as the production canonical domain.
