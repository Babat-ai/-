// Playwrightで1/30秒ずつ撮影し ffmpeg で動画化（区間を指定して並列実行）
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { spawn } = require('child_process');
const TL = require('./voice/timeline.json');
(async () => {
  const FPS = 30, N = Math.ceil(TL.total * FPS);
  const W = +process.argv[2], K = +process.argv[3];
  const a = Math.floor(N * W / K), b = Math.floor(N * (W + 1) / K);
  const br = await chromium.launch({executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
  const p = await br.newPage({viewport: {width: 1920, height: 1080}});
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + __dirname + '/render.html'); await p.evaluate(() => window.ready);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', `part${W}.mp4`], {stdio: ['pipe', 'inherit', 'inherit']});
  const t0 = Date.now();
  for (let i = a; i < b; i++) {
    await p.evaluate(t => window.seek(t), i / FPS);
    const buf = await p.screenshot({type: 'jpeg', quality: 92});
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((i - a) % 300 === 0) console.log(`w${W} ${i - a}/${b - a} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await br.close(); console.log(`w${W} done`);
})();
