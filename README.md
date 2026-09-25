# Kings Tourism Crest — Flask web app

The public site has no Admin button. Admin is a private login route at `/admin/login`. The Flask backend stores inquiries in SQLite and tracks page views plus a random-cookie unique visitor estimate without storing IP addresses.

## Run in VS Code / Windows
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:ADMIN_USERNAME="gaurav"
$env:ADMIN_PASSWORD="YOUR_STRONG_PASSWORD"
$env:SECRET_KEY="YOUR_LONG_RANDOM_SECRET"
$env:WHATSAPP_NUMBER="919876543210"
python app.py
```
Public: http://127.0.0.1:5000/
Admin: http://127.0.0.1:5000/admin/login

For production, use HTTPS, a persistent hosted database, environment variables, CSRF/rate limiting, and an appropriate privacy notice.

### Landing-page contact
The landing page shows **Nidhi Jain** as the travel contact with WhatsApp/phone **+91 96535 50755**.


### Travel card videos
Put your two MP4 videos here:
- `static/videos/international.mp4` — plays in the International card
- `static/videos/domestic.mp4` — plays in the Domestic card

The videos are set to autoplay, muted, loop and playsinline so they behave like cinematic card backgrounds.
