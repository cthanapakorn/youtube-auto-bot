# Swat In Home — External run

This is a responsive web/PWA build. It runs in a desktop browser and can be installed on a phone as a standalone app.

## Start locally

From this `outputs` folder, run one of these commands:

```powershell
python -m http.server 8765
```

Then open:

```text
http://localhost:8765/field-service-prototype.html
```

For phone testing on the same Wi‑Fi, use the computer's LAN address instead of `localhost`, for example:

```text
http://192.168.1.20:8765/field-service-prototype.html
```

The app includes `manifest.webmanifest` and `sw.js`, so supported browsers can install it as a PWA. Service workers require `localhost` or HTTPS; opening the HTML directly with `file://` is not supported.
