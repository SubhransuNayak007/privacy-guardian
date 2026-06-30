const Tesseract = require('tesseract.js');
async function test() {
  console.log('Starting...');
  const worker = await Tesseract.createWorker('eng');
  const { data } = await worker.recognize('public/privacy-guardian-logo.png');
  console.log('Text:', data.text);
  console.log('Words count:', data.words ? data.words.length : 'undefined');
  if (data.words && data.words.length > 0) {
    console.log('First word:', data.words[0]);
  }
  await worker.terminate();
}
test();
