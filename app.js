const qs = (s)=>document.querySelector(s);
const $image = qs('#imageInput');
const $predictBtn = qs('#predictBtn');
const $predictResult = qs('#predictResult');
const $reportSection = qs('#report-section');
const $filenameInput = qs('#filenameInput');
const $saveReportBtn = qs('#saveReportBtn');
const $reportSaved = qs('#reportSaved');
const $reportsUl = qs('#reportsUl');
const $refreshReportsBtn = qs('#refreshReportsBtn');
const $fbName = qs('#fbName');
const $fbEmail = qs('#fbEmail');
const $fbKind = qs('#fbKind');
const $fbRating = qs('#fbRating');
const $fbMsg = qs('#fbMsg');
const $fbSend = qs('#fbSend');
const $fbStatus = qs('#fbStatus');

function pretty(obj){
  return JSON.stringify(obj, null, 2);
}

async function predict(){
  if(!$image.files[0]){ alert('Select an image'); return; }
  const fd = new FormData();
  fd.append('file', $image.files[0]);
  $predictBtn.disabled = true;
  try{
    const res = await fetch('/predict', { method:'POST', body: fd });
    if(!res.ok) throw new Error('Predict failed');
    const data = await res.json();
    $predictResult.classList.remove('hidden');
    $predictResult.textContent = pretty(data);
    $reportSection.classList.remove('hidden');
    $filenameInput.value = $image.files[0].name || 'upload.jpg';
    $saveReportBtn.onclick = ()=> saveReport(data);
  }catch(e){
    alert(e.message || 'Error');
  }finally{
    $predictBtn.disabled = false;
  }
}

async function saveReport(pred){
  const payload = {
    filename: $filenameInput.value || 'upload.jpg',
    disease: pred.disease,
    confidence: pred.confidence,
    severity: pred.severity,
    recommendations: pred.recommendations || [],
    treatment: pred.treatment || [],
    annotated_image: null
  };
  $saveReportBtn.disabled = true;
  try{
    const res = await fetch('/reports', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if(!res.ok) throw new Error('Save failed');
    const row = await res.json();
    $reportSaved.textContent = `Saved report #${row.id}`;
    await loadReports();
  }catch(e){
    alert(e.message || 'Error');
  }finally{
    $saveReportBtn.disabled = false;
  }
}

async function loadReports(){
  $reportsUl.innerHTML = '';
  try{
    const res = await fetch('/reports');
    if(!res.ok) throw new Error('Load reports failed');
    const list = await res.json();
    list.forEach(r=>{
      const li = document.createElement('li');
      const conf = Math.round((r.confidence||0)*100);
      li.innerHTML = `<strong>#${r.id}</strong> ${r.filename||''} — ${r.disease} (${conf}%) <a href="/reports/${r.id}/download">Download</a>`;
      $reportsUl.appendChild(li);
    });
  }catch(e){
    const li = document.createElement('li');
    li.textContent = e.message || 'Error loading reports';
    $reportsUl.appendChild(li);
  }
}

async function sendFeedback(){
  $fbSend.disabled = true;
  $fbStatus.textContent = '';
  try{
    const payload = {
      name: $fbName.value.trim(),
      email: $fbEmail.value.trim(),
      message: $fbMsg.value.trim() || null,
      kind: $fbKind.value,
      rating: $fbRating.value? Number($fbRating.value): null
    };
    const res = await fetch('/feedback', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if(!res.ok){
      const t = await res.text();
      throw new Error(t || 'Feedback failed');
    }
    $fbStatus.textContent = 'Thank you';
    $fbName.value = '';
    $fbEmail.value = '';
    $fbMsg.value = '';
    $fbRating.value = '';
  }catch(e){
    $fbStatus.textContent = e.message || 'Error';
  }finally{
    $fbSend.disabled = false;
  }
}

$predictBtn.addEventListener('click', predict);
$refreshReportsBtn.addEventListener('click', loadReports);
$fbSend.addEventListener('click', sendFeedback);

loadReports();
