# Landscape Planner

A self-hosted, mobile-friendly web app for managing a plant database and designing garden layouts. Identify plants from photos, look up full botanical data, and drag plants onto a canvas map of your yard.

---

## Features

- **Plant identification** — upload and crop a photo, PlantNet identifies the plant with confidence scores
- **Full botanical data** — Trefle.io auto-fills every field: light, water, pH, temperature, bloom months, toxicity, foliage, fruit, height, synonyms, and more
- **Plant database** — browse, search, edit, and delete plants; all photos and data stored locally
- **Canvas design** — drag plants from your database onto a background image of your yard; pan, zoom, resize, and layer
- **Mobile-friendly** — pinch-to-zoom, two-finger pan, touch drag-and-drop, bottom-sheet plant gallery
- **Multi-user** — simple username/password auth, no email required
- **Fully self-hosted** — all assets served locally, no internet required after setup

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- A free [PlantNet API key](https://my.plantnet.org) (500 identifications/day)
- A free [Trefle.io token](https://trefle.io) (plant botanical data)

---

## Installation

### 1. Clone or copy the project

```bash
git clone <your-repo-url> landscape-plan
cd landscape-plan
```

Or just copy the `landscape-plan` folder to your server.

### 2. Create the user accounts file

```bash
nano .users
```

Add one account per line in `username:password` format:

```
admin:changeme
alice:mypassword
bob:anotherpassword
```

### 3. Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
nano .env
```

```ini
# Plant identification — free 500/day at https://my.plantnet.org
PLANT_ID_PROVIDER=plantnet
PLANTNET_API_KEY=your_plantnet_key_here

# Trefle botanical data — free token at https://trefle.io
TREFLE_API_KEY=your_trefle_token_here

# Change this to any long random string
SECRET_KEY=change-me-to-something-random
```

### 4. Add a canvas background image (optional)

Place a top-down photo or sketch of your yard at:

```
data/canvas.png
```

Any image format works (PNG, JPG). The canvas displays it at 3× size. If no image is present the canvas will still work with a plain background.

### 5. Start the app

```bash
docker compose up -d
```

The app builds automatically on first run. Open it at:

```
http://your-server-ip:40070
```

---

## Upgrading / applying code changes

Because the app code is copied into the image at build time, any update requires a rebuild:

```bash
docker compose up -d --build
```

Your data in `./data/` and your `.users` and `.env` files are never touched by a rebuild.

---

## Directory structure

```
landscape-plan/
├── docker-compose.yml
├── Dockerfile
├── .env                  # API keys and secret (you create this)
├── .users                # username:password accounts (you create this)
├── data/                 # all persistent data (auto-created)
│   ├── canvas.png        # your yard background image
│   ├── plants.db         # SQLite plant database
│   ├── uploads/          # full-size plant photos
│   └── thumbnails/       # auto-generated thumbnails
└── app/                  # application source code
```

---

## Usage

### Logging in

Navigate to `http://your-server-ip:40070` and log in with any username and password from your `.users` file.

---

### Plant Database

#### Adding a plant via photo

1. Click **Plant Database** → **Add Plant via Photo**
2. Choose a photo from your device and click **Upload & Crop**
3. Drag the crop box over the plant, then click **Crop & Identify**
4. PlantNet returns up to 5 matches with confidence scores
5. Click **Select This Plant** on the best match — all botanical fields are pre-filled from Trefle
6. Review the common name, scientific name, and description, then click **Save to Plant Database**

#### Editing a plant

Click any plant card in the database. The detail page has six accordion sections:

| Section | Fields |
|---|---|
| Identity & Taxonomy | Name, family, genus, rank, status, year, author, duration, edible, synonyms |
| Growth Conditions | Light (0–10), soil humidity, atmospheric humidity, pH, temperature, precipitation, root depth |
| Seasons | Bloom months, growth months, fruit months |
| Appearance | Flower color, foliage texture/color, leaf retention, fruit color/shape |
| Characteristics | Toxicity, ligneous type, growth rate, height, spread, nitrogen fixation |
| Description & Cultivation | Description, observations, sowing instructions |

The **Personal Notes** section is for your own notes — planting location, purchase source, etc.

#### Adding a plant manually

Click **Add Manually** to open a blank detail form. Fill in whatever fields you know and save.

---

### Canvas Design

#### Setup

Place a top-down photo of your yard at `data/canvas.png`. The canvas displays it at 3× its original size.

#### Placing plants

**Desktop:**
- The left sidebar lists all plants in your database
- Drag a plant tile and drop it onto the canvas

**Mobile:**
- Tap **Plants** in the toolbar to open the plant gallery
- Press and hold a plant tile, drag your finger over the canvas, and release

#### Navigating the canvas

| Action | Desktop | Mobile |
|---|---|---|
| Zoom in/out | Scroll wheel, or +/− buttons | Pinch two fingers |
| Pan | Alt + drag, or Pan Mode button | Two fingers drag, or Pan Mode button |
| Pan Mode | Click the ↕ button in the toolbar | Tap the ↕ button |

**Pan Mode** lets a single finger/click pan the view instead of selecting objects. Tap the button again to return to select mode.

#### Editing objects

- **Move** — drag any plant image
- **Resize** — click to select, then drag the corner handles
- **Bring forward / Send backward** — use the layer buttons in the toolbar
- **Delete** — select an object and click the trash button (or press Delete/Backspace)

#### Saving

Click **Save** in the toolbar. The layout is saved to `data/canvas_state.json` and reloads automatically next time you open the canvas. You will be warned if you try to leave with unsaved changes.

---

## Changing ports

Edit `docker-compose.yml` and change `40070` to any port you prefer:

```yaml
ports:
  - "8080:8000"
```

Then restart: `docker compose up -d`

---

## Adding or removing users

Edit `.users` directly — no restart required, the file is read on every login:

```bash
nano .users
```

To remove a user, delete their line. To add one, append a new `username:password` line.

---

## Resetting the plant database

```bash
docker compose down
rm data/plants.db
docker compose up -d
```

This deletes all plant records. Photos in `data/uploads/` and `data/thumbnails/` are not deleted automatically — remove them manually if desired.

---

## API keys

| Key | Where to get | Free tier |
|---|---|---|
| `PLANTNET_API_KEY` | [my.plantnet.org](https://my.plantnet.org) | 500 identifications/day |
| `TREFLE_API_KEY` | [trefle.io](https://trefle.io) | Free with registration |

If `TREFLE_API_KEY` is not set, botanical fields will be blank after identification. If `PLANTNET_API_KEY` is not set, the identification step will fail but plants can still be added manually.
