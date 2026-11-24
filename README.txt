WEDDING INVITATION STUDIO — FLASK

FEATURES:
- Multiple invitations with unique URLs (/invite/slug).
- Admin panel to create, edit, delete, and view RSVPs.
- Per-invitation uploads: Hero photo, multiple gallery photos, background music.
- 5 Themes: Royal Gold, Pink Floral, Traditional, Green Garden, Modern Luxury.
- Google Maps location button for guests.
- Countdown timer and guest RSVP form.

HOW TO RUN (Windows):
1. Open Terminal in VS Code.
2. Run these commands:
   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   
3. Set admin password:
   $env:ADMIN_PASSWORD="your-password"

4. Start server:
   python app.py
   Open: http://127.0.0.1:5000

SHARING LINK (IMPORTANT):
- If you use http://127.0.0.1:5000, the link works ONLY on your laptop.
- To share with wedding guests, you MUST deploy this app online.
- Deploy to Render.com or PythonAnywhere.com and get a public URL (e.g., https://mywedding.onrender.com/invite/slug).
- Send that public URL on WhatsApp so all guests can open it.