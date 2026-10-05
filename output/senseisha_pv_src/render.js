const { chromium } = require('playwright');
const { spawn } = require('child_process');
(async () => {
  const FPS=30, DUR=90, N=FPS*DUR;
  const b = await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
  const p = await b.newPage({viewport:{width:1920,height:1080}});
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + __dirname + '/render.html'); await p.evaluate(() => window.ready);
  const ff = spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-',
    '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','video_only.mp4'],{stdio:['pipe','inherit','inherit']});
  const t0=Date.now();
  for (let i=0;i<N;i++){
    await p.evaluate(t => window.seek(t), i/FPS);
    const buf = await p.screenshot({type:'jpeg',quality:93});
    if (!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
    if (i%300===0) console.log(`frame ${i}/${N} ${((Date.now()-t0)/1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close(); console.log('done');
})();
