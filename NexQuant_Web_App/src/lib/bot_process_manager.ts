import { spawn, exec } from 'child_process';
import path from 'path';
import fs from 'fs';

const SUPERBOT_DIR = path.resolve(process.cwd(), '../superbot');
const PID_FILE = path.join(SUPERBOT_DIR, '.bot.pid');

export async function startBotProcess() {
  if (fs.existsSync(PID_FILE)) {
    const pid = fs.readFileSync(PID_FILE, 'utf-8').trim();
    try {
      if (process.platform === 'win32') {
        // on Windows, process.kill(pid, 0) can throw if process doesn't exist
      }
      process.kill(Number(pid), 0);
      console.log(`[BotManager] Bot already running with PID ${pid}`);
      return true;
    } catch (e) {
      console.log(`[BotManager] Stale PID file found. Cleaning up.`);
      fs.unlinkSync(PID_FILE);
    }
  }

  console.log(`[BotManager] Starting Python bot in ${SUPERBOT_DIR}...`);
  // Démarrage du processus Python de manière détachée
  const child = spawn('python', ['main.py'], {
    cwd: SUPERBOT_DIR,
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  });

  child.unref(); // Permet à Node de s'arrêter sans attendre le processus enfant

  if (child.pid) {
    fs.writeFileSync(PID_FILE, child.pid.toString());
    console.log(`[BotManager] Bot started with PID ${child.pid}`);
    return true;
  }
  return false;
}

export async function stopBotProcess() {
  if (fs.existsSync(PID_FILE)) {
    const pid = fs.readFileSync(PID_FILE, 'utf-8').trim();
    try {
      console.log(`[BotManager] Killing bot process ${pid}...`);
      if (process.platform === 'win32') {
        // Force kill tree on Windows
        await new Promise((resolve) => {
          exec(`taskkill /PID ${pid} /T /F`, (err, stdout, stderr) => {
            if (err) console.error(`[BotManager] taskkill error:`, err);
            resolve(true);
          });
        });
      } else {
        process.kill(Number(pid), 'SIGTERM');
      }
      console.log(`[BotManager] Bot process ${pid} killed.`);
    } catch (e) {
      console.log(`[BotManager] Failed to kill bot process ${pid} or it was already dead.`);
    }
    try {
      fs.unlinkSync(PID_FILE);
    } catch (e) {
      // ignore
    }
  } else {
    console.log("[BotManager] No .bot.pid found. Bot is likely not running locally.");
  }
}
