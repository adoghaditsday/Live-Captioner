import fs from "fs";

const CAPTION_QUEUE_FILE = "C:/PATH/TO/GSG3_Live_Captioner/output/twitch_chat_queue.txt";

const lastCaptionByChannel = new Map();
const lastPostTimeByChannel = new Map();

function getLatestCaptionFromFile(filePath) {
  const raw = fs.readFileSync(filePath, "utf8").trim();
  if (!raw) return "";
  const lines = raw.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  return lines[lines.length - 1] || "";
}

export function startCaptionWatcher(client, channelName) {
  const cleanChannel = String(channelName).replace(/^#/, "").trim();
  const twitchChannel = `#${cleanChannel}`;

  console.log("[Caption Watcher] Watching:", CAPTION_QUEUE_FILE);
  console.log("[Caption Watcher] File exists:", fs.existsSync(CAPTION_QUEUE_FILE));
  console.log("[Caption Watcher] Posting to:", twitchChannel);

  fs.watchFile(CAPTION_QUEUE_FILE, { interval: 500 }, async () => {
    try {
      if (!fs.existsSync(CAPTION_QUEUE_FILE)) return;
      const text = getLatestCaptionFromFile(CAPTION_QUEUE_FILE);
      if (!text) return;

      const lastCaption = lastCaptionByChannel.get(twitchChannel);
      if (text === lastCaption) return;

      const now = Date.now();
      const lastPostTime = lastPostTimeByChannel.get(twitchChannel) || 0;
      if (now - lastPostTime < 5000) return;

      lastCaptionByChannel.set(twitchChannel, text);
      lastPostTimeByChannel.set(twitchChannel, now);

      await client.say(twitchChannel, `[Streamer]: ${text}`);
      console.log(`[Caption Watcher] Posted to ${twitchChannel}: ${text}`);
    } catch (err) {
      console.error(`[Caption Watcher Send Error] ${twitchChannel}`, err);
    }
  });
}
