# World News for Kids: Alexa Flash Briefing

A private Alexa Flash Briefing that reads 5 short, kid-friendly world news stories.
It runs for free on GitHub: a scheduled job rebuilds the feed three times a day, and GitHub Pages hosts it.

```
newsforkids.net ┐
kiwikidsnews    ├─> fetch_news.py ─> docs/feed.json ─> GitHub Pages (HTTPS) ─> Alexa
BBC Newsround   ┘   (clean, filter,   (Flash Briefing
                     pick 5 freshest)   JSON format)
```

## Part 1: Publish the feed (about 10 minutes)

1. Create a new GitHub repository, for example `kids-news-feed`, and upload everything in this folder, including the hidden `.github` folder.
2. Go to **Actions → Update kids news feed → Run workflow**. Wait about 30 seconds and check that the run turns green. `docs/feed.json` should now appear in the repo.
3. Go to **Settings → Pages → Build and deployment**, set Source to *Deploy from a branch*, and pick Branch `main` with folder `/docs`. Save.
4. After a minute or two, open `https://<your-username>.github.io/kids-news-feed/feed.json`. You should see 5 stories. Copy this URL for Part 2.

> The repository has to be **public** for GitHub Pages to work on a free account. The feed only contains short excerpts with links back to each outlet, much like any RSS reader shows.

## Part 2: Create the Alexa skill (about 10 minutes)

1. Sign in at **developer.amazon.com/alexa/console/ask** with the same Amazon account your Echo uses.
2. Click **Create Skill**, name it *World News for Kids*, and set the **locale to match your Echo's language** (for example English (UK) or English (US)). Choose the **Flash Briefing** model and create the skill.
3. Enter a short message for errors, for example "World news for kids isn't available right now."
4. Click **Add new feed** and fill in:
   - **Preamble:** the short intro line Alexa says before the stories
   - **Name:** World News for Kids
   - **Update frequency:** Daily (or Hourly)
   - **Content type:** Text
   - **Genre:** News
   - **Icon:** any 512×512 PNG or JPG
   - **URL:** the feed URL from Part 1
5. Save. Then open the **Test** tab and set testing to **Development**.

You don't need to submit the skill for certification. Development skills work on every Echo signed in to your developer account.

## Part 3: Turn it on at home

- In the Alexa app, go to **More → Settings → News → Flash Briefing**. Turn on *World News for Kids*, then turn off any adult news sources you don't want her to hear, or move them further down the list.
- She can now say **"Alexa, what's the news?"** or **"Alexa, what's my flash briefing?"**
- Optional: create a routine with a phrase like "Alexa, good morning" or a set time such as 07:30 on school days, and add the **News** action.

> If her Echo uses an **Amazon Kids** profile, check that third-party content and news are allowed in the Amazon Parent Dashboard. Kids profiles can block skills that work on the adult profile.

## Customising

All the settings are at the top of `fetch_news.py`:

| Setting | What it does |
|---|---|
| `SOURCES` | Add or remove RSS feeds. A feed that fails is skipped, so the rest of the briefing still plays. |
| `BLOCKLIST` | Skips any story containing these words. Add words to make filtering stricter. |
| `MAX_AGE_DAYS` | How old a story can be. Keep this under 7, because Alexa ignores older items. |
| `MAX_SUMMARY_CHARS` | Length of each story. 420 characters takes about 20–25 seconds to read. |

To change when the feed updates, edit the `cron` line in `.github/workflows/update-feed.yml`. The times are in UTC.

## Troubleshooting

- **Alexa reads old news:** Open the Actions tab and check whether recent runs succeeded. Alexa checks feeds every 15 minutes, and new stories can take up to 30 minutes to play.
- **A source keeps failing:** The run log shows a `WARN <source>` line. Swap that feed for another one in `SOURCES`.
- **GitHub stops the schedule:** GitHub pauses scheduled workflows in repos with no activity for 60 days. The bot's own commits normally count as activity, but if the schedule ever stops, re-enable it from the Actions tab.
