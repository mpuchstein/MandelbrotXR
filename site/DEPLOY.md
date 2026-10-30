# Deploying the MandelbrotXR results site

Recommendations only, for the owner to apply. The build does not deploy anything.

## Build

From a clean clone, at the repository root (stdlib only, Python ≥ 3.11):

```bash
python3 -I site/build.py --out site/dist
```

The output directory (`site/dist/`, gitignored) is the complete site. Serve it as the web root of
`https://mandelbrotxr.puchstein.dev/`. `--base-url` (default `https://mandelbrotxr.puchstein.dev/`) only
changes the QR codes, the Atom feed and the canonical links; everything else is relative, so the same
build also works under any path prefix.

The build needs the git history (changelog and feed). A shallow clone is unshallowed automatically
(`git fetch --unshallow`), so the build host needs network access to the remote in that case.

## WebXR requires HTTPS

WebXR sessions (`navigator.xr.requestSession`) only exist in a secure context. Serve the site over
HTTPS (Caddy does this automatically); over plain HTTP the products load, but "Enter VR/AR" fails on
every headset and phone. `localhost` counts as secure for local testing.

## Caddy

Two policies: strict for site pages, permissive for the products under `/play/*`. The products are
untouched single-file HTML pages with inline scripts and styles; one of them
(`Google-Web-Gemini4Argon-High-v1`) loads three.js r128 from `cdnjs.cloudflare.com`, the Tailwind play
CDN from `cdn.tailwindcss.com` and fonts from Google Fonts at runtime.

```caddyfile
mandelbrotxr.puchstein.dev {
	root * /srv/mandelbrotxr/site/dist
	encode zstd gzip

	# never serve repository internals if the site is deployed from a checkout
	@hidden path /.git /.git/* */.git/* /.mandelbrotxr-site
	respond @hidden 404

	header {
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		Strict-Transport-Security "max-age=31536000"
		-Server
	}

	# site pages: strict CSP (the build has no inline scripts, no on*= handlers, no third-party requests)
	@site not path /play/*
	header @site {
		Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'self'"
		Permissions-Policy "camera=(), microphone=(), geolocation=()"
	}

	# products: inline scripts/styles + the Gemini CDNs, and the sensor/XR features WebXR needs
	header /play/* {
		Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self' data: blob:; worker-src 'self' blob:; frame-ancestors 'self'"
		Permissions-Policy "xr-spatial-tracking=(self), gyroscope=(self), accelerometer=(self), magnetometer=(self)"
	}

	# caching: hashed assets are immutable (URLs carry ?v=<content hash>); pages revalidate
	@assets path /assets/*
	header @assets Cache-Control "public, max-age=31536000, immutable"
	@media path /media/*
	header @media Cache-Control "public, max-age=604800"
	@data path /data/* /search-index/* /feed.xml
	header @data Cache-Control "public, max-age=300, must-revalidate"
	@pages path *.html */
	header @pages Cache-Control "public, max-age=0, must-revalidate"

	file_server
}
```

Notes:
- If you prefer no CSP at all for `/play/*`, drop that `Content-Security-Policy` line but keep the
  `Permissions-Policy`. `'unsafe-eval'` and `blob:` are listed because bundled three.js builds and the
  Tailwind play CDN may compile code or spawn workers at runtime; tighten them only after testing every
  product on a headset.
- `Permissions-Policy` for `/play/*` allows `xr-spatial-tracking`, `gyroscope`, `accelerometer` and
  `magnetometer` for `self`, which the products need for immersive sessions and the phone
  "look around" fallbacks. Site pages do not need them.
- The search index (`/search-index/*.json`) and `data/*.json` are plain static files; compression helps.
- `.mandelbrotxr-site` is a marker the build writes so it never wipes a foreign directory; it is harmless
  but need not be served.

## Checks after deploying

```bash
curl -sI https://mandelbrotxr.puchstein.dev/ | grep -i content-security-policy
```

```bash
curl -sI https://mandelbrotxr.puchstein.dev/play/opus55-max-v1/ | grep -i permissions-policy
```

Then open a product on a Quest or an Android phone and enter VR/AR.
