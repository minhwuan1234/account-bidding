const files=document.querySelector('#files'), status=document.querySelector('#status'), candidateBox=document.querySelector('#candidates'), exportBtn=document.querySelector('#export'),compareBox=document.querySelector('#compare'),compareRetry=document.querySelector('#compare-retry'),compareStatus=document.querySelector('#compare-status'),compareResults=document.querySelector('#compare-results'),libraryUpload=document.querySelector('#library-upload'),libraryStatus=document.querySelector('#library-status'),libraryList=document.querySelector('#library-list');let latest=[],latestMatch=null,latestReport=null,library=[],llmReady=false,analysisRevision=0,suggestionGeneration=0,suggestionTimer=null,suggestionAbortController=null,lastSuggestionKey='',activeSuggestionKey='';const tagPreview=document.querySelector('#tag-preview'),tagDialog=document.querySelector('#tag-dialog'),reviewButton=document.querySelector('#review-tags');function updateOverview(){document.querySelector('#metric-documents').textContent=latest.length;document.querySelector('#metric-tags').textContent=nextStepTags().length;document.querySelector('#metric-library').textContent=library.length}
let activeBidId=null,activeBidTitle='',bidSaveQueue=Promise.resolve(),bidSaveTimer=null;
const historyList=document.querySelector('#history-list'),historyStatus=document.querySelector('#history-status');
function saveBidSnapshot(nextStatus){
 if(!activeBidId)return Promise.resolve();
 const bidId=activeBidId;activeBidTitle=(latestReport?.title||activeBidTitle).slice(0,255);
 const payload=JSON.stringify({title:activeBidTitle,status:nextStatus||((latestReport)?'complete':'processing'),documents:latest,matches:latestMatch,report:latestReport});
 const task=async()=>{const response=await fetch('/api/bids?id='+encodeURIComponent(bidId),{method:'PUT',headers:{'Content-Type':'application/json'},body:payload});const data=await response.json();if(!response.ok)throw Error(data.error||'Không lưu được lịch sử bid');return data.bid};
 bidSaveQueue=bidSaveQueue.catch(()=>{}).then(task);return bidSaveQueue;
}
function scheduleBidSave(){saveBidSnapshot().catch(error=>{reportStatus.className='error';reportStatus.textContent='Không lưu được thay đổi vào lịch sử: '+error.message})}
async function deleteHistoryBid(bid){
 if(activeRun&&bid.id===activeBidId){historyStatus.className='error';historyStatus.textContent='Đợi bid đang xử lý hoàn tất trước khi xóa.';return}
 if(!window.confirm(`Xóa bid “${bid.title}” khỏi lịch sử?`))return;
 try{await bidSaveQueue.catch(()=>{});const response=await fetch('/api/bids?id='+encodeURIComponent(bid.id),{method:'DELETE'});const data=await response.json();if(!response.ok)throw Error(data.error||'Không xóa được bid');if(activeBidId===bid.id){clearTimeout(bidSaveTimer);activeBidId=null}await loadBidHistory();historyStatus.className='';historyStatus.textContent='Đã xóa bid khỏi lịch sử.'}catch(error){historyStatus.className='error';historyStatus.textContent='Không xóa được bid: '+error.message}
}
async function loadBidHistory(){
 historyStatus.className='';historyStatus.textContent='Đang tải lịch sử…';
 try{await bidSaveQueue.catch(()=>{});const response=await fetch('/api/bids');const data=await response.json();if(!response.ok)throw Error(data.error||'Không tải được lịch sử');historyList.replaceChildren();
 if(!data.bids.length){historyList.append(el('p','history-empty','Chưa có bid nào. Tải tài liệu ở tab Tổng quan bid để bắt đầu.'));historyStatus.textContent='';return}
 const wrap=el('div','history-table-wrap'),table=el('table','history-table'),thead=el('thead'),header=el('tr');for(const label of ['Bid','Bên mời thầu','Hạn nộp','Hồ sơ',''])header.append(el('th','',label));thead.append(header);table.append(thead);const body=el('tbody');
 for(const bid of data.bids){const row=el('tr'),name=el('td'),created=new Date(bid.created_at),buyer=el('td','',bid.buyer||'Chưa rõ'),dateCell=el('td'),docs=el('td'),actions=el('td','history-actions');name.append(el('strong','',bid.title));if(!Number.isNaN(created.getTime()))name.append(el('div','history-meta',created.toLocaleString('vi-VN')));
 const deadline=bid.submission_deadline;if(deadline?.value){dateCell.append(el('div','',deadline.value));const [label,cls]=deadline.conditional?['Theo điều kiện','unknown']:deadlineStatus(deadline.value);dateCell.append(el('span','report-date-status '+cls,label))}else dateCell.append(el('span','history-muted','Chưa rõ'));
 if(bid.has_report){const total=Number(bid.requirement_count)||0,selected=Number(bid.selected_count)||0;docs.append(el('span','report-status-tag '+(total&&selected===total?'has-file':'missing-file'),total?`Đã có ${selected}/${total}`:'Không có yêu cầu'))}else docs.append(el('span','history-muted','Chưa có báo cáo'));
 const open=el('button','secondary','Mở'),remove=el('button','history-delete','Xóa');open.type=remove.type='button';open.onclick=()=>openBid(bid.id);remove.onclick=()=>deleteHistoryBid(bid);remove.setAttribute('aria-label',`Xóa bid ${bid.title}`);actions.append(open,remove);row.append(name,buyer,dateCell,docs,actions);body.append(row)}table.append(body);wrap.append(table);historyList.append(wrap);historyStatus.textContent=''
 }catch(error){historyStatus.className='error';historyStatus.textContent='Không tải được lịch sử: '+error.message}
}
async function openBid(bidId){if(activeRun){historyStatus.textContent='Đợi bid hiện tại xử lý xong rồi mở bid khác.';return}historyStatus.textContent='Đang mở bid…';try{await bidSaveQueue.catch(()=>{});const response=await fetch('/api/bids?id='+encodeURIComponent(bidId));const data=await response.json();if(!response.ok)throw Error(data.error||'Không mở được bid');clearTimeout(suggestionTimer);clearTimeout(bidSaveTimer);suggestionGeneration++;suggestionAbortController?.abort();reportGeneration++;analysisRevision++;lastSuggestionKey='';activeSuggestionKey='';reportOverrides.clear();activeBidId=bidId;activeBidTitle=data.bid.title;latest=data.bid.documents||[];latestMatch=data.bid.matches||null;latestReport=data.bid.report||null;renderCandidates();if(latestMatch)renderTagResults(latestMatch.tag_matches||[]);else compareResults.replaceChildren();compareBox.hidden=!(latestMatch?.tag_matches?.length);exportBtn.disabled=!latest.length;reportStatus.className='meta';reportStatus.textContent='';if(latestReport)renderBidReport();else{reportBox.replaceChildren();reportToolbar.hidden=!latest.length;reportRun.disabled=!latest.length;reportStatus.textContent='Bid này chưa có bản tổng hợp. Bấm “Tạo lại” để tiếp tục.'}hideProcessingFiles();historyStatus.textContent='';setTab('analysis')}catch(error){historyStatus.className='error';historyStatus.textContent='Không mở được bid: '+error.message}}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
const processingFiles=document.querySelector('#processing-files');function showProcessingFiles(names,phase='Đang phân tích'){const filesToShow=names?.length?names:latest.map(doc=>doc.file).filter(Boolean);processingFiles.textContent=phase+(filesToShow.length?': '+filesToShow.join(' · '):'…');processingFiles.hidden=false}function hideProcessingFiles(){processingFiles.hidden=true;processingFiles.textContent=''}
const processingLog=document.querySelector('#processing-log'),processingLogLines=document.querySelector('#processing-log-lines');
function clearProcessingLog(){processingLogLines.replaceChildren();processingLog.hidden=true}
function appendProcessingLog(state,message){const row=el('li');row.dataset.state=state;const time=el('time','',new Date().toLocaleTimeString('vi-VN',{hour12:false}));row.append(time,el('span','',message));processingLogLines.append(row);processingLog.hidden=false;processingLogLines.scrollTop=processingLogLines.scrollHeight}
const dropZone=document.querySelector('#drop-zone'),chosenFiles=document.querySelector('#chosen-files'),runButton=document.querySelector('#run');function updateRunButton(){runButton.disabled=!files.files.length||!!activeRun}function updateChosenFiles(){chosenFiles.replaceChildren();for(const file of files.files)chosenFiles.append(el('span','',file.name));chosenFiles.hidden=!files.files.length;updateRunButton()}
files.addEventListener('click',()=>{files.value='';updateChosenFiles()});files.addEventListener('change',updateChosenFiles);
for(const name of ['dragenter','dragover'])dropZone.addEventListener(name,event=>{event.preventDefault();if(!files.disabled)dropZone.classList.add('drag-over')});
dropZone.addEventListener('dragleave',event=>{if(!dropZone.contains(event.relatedTarget))dropZone.classList.remove('drag-over')});
dropZone.addEventListener('drop',event=>{event.preventDefault();dropZone.classList.remove('drag-over');if(files.disabled)return;const picked=[...event.dataTransfer.files].filter(file=>/\.(pdf|docx)$/i.test(file.name));if(!picked.length){status.textContent='Chỉ nhận PDF hoặc DOCX.';status.className='error';return}const transfer=new DataTransfer();for(const file of picked)transfer.items.add(file);files.files=transfer.files;updateChosenFiles()});
const metricsBox=document.querySelector('#run-metrics');let activeRun=null,runHistory=[],metricsTimer=null,runSequence=0;
function metricCost(run){if(run.unknownCost)return run.costUsd>0?`≥ $${run.costUsd.toFixed(6)} (chưa đủ dữ liệu)`:'Chưa xác định';return `$${run.costUsd.toFixed(6)}`}
function metricDuration(run){return (((run.endedAt??performance.now())-run.startedAt)/1000).toFixed(1)+' giây'}
function renderRunMetrics(){metricsBox.replaceChildren();const run=activeRun||runHistory[0];metricsBox.hidden=!run;if(!run)return;metricsBox.title=run.unknownCost?'Chi phí API chưa đầy đủ vì thiếu đơn giá hoặc dữ liệu token.':'Chi phí API ước tính từ token; hóa đơn thực tế có thể khác.';for(const [label,value] of [['Thời gian',metricDuration(run)],['Chi phí',metricCost(run)]]){const stat=el('span');stat.append(document.createTextNode(label+' '),el('b','',value));metricsBox.append(stat)}}
function startRun(label){if(activeRun)finishRun('Đã dừng');activeRun={id:++runSequence,label,startedAt:performance.now(),endedAt:null,inputTokens:0,outputTokens:0,costUsd:0,calls:0,unknownCost:false,note:''};updateRunButton();clearInterval(metricsTimer);metricsTimer=setInterval(renderRunMetrics,1000);renderRunMetrics();return activeRun.id}
function ensureRun(label){return activeRun?.id||startRun(label)}
function addRunUsage(usage,id=activeRun?.id){if(!activeRun||activeRun.id!==id)return;activeRun.calls++;if(!usage){activeRun.unknownCost=true;renderRunMetrics();return}activeRun.inputTokens+=Number(usage.input_tokens)||0;activeRun.outputTokens+=Number(usage.output_tokens)||0;if(typeof usage.estimated_cost_usd==='number')activeRun.costUsd+=usage.estimated_cost_usd;else activeRun.unknownCost=true;renderRunMetrics()}
function finishRun(note){if(!activeRun)return;activeRun.endedAt=performance.now();activeRun.note=note;runHistory.unshift(activeRun);activeRun=null;updateRunButton();clearInterval(metricsTimer);metricsTimer=null;renderRunMetrics()}
function showTagPreview(button,topic,chunks,event){tagPreview.replaceChildren(el('strong','',topic),el('span','',chunks.map(item=>item.text).join('\n\n').slice(0,2500)));tagPreview.hidden=false;const rect=button.getBoundingClientRect(),x=event&&Number.isFinite(event.clientX)?event.clientX:rect.left,y=event&&Number.isFinite(event.clientY)?event.clientY:rect.bottom;tagPreview.style.left=Math.max(12,Math.min(x+14,innerWidth-tagPreview.offsetWidth-12))+'px';tagPreview.style.top=Math.max(12,Math.min(y+18,innerHeight-tagPreview.offsetHeight-12))+'px'}
function hideTagPreview(){tagPreview.hidden=true}
function setTab(name){for(const tab of ['analysis','history','library']){const selected=tab===name;document.querySelector('#tab-'+tab).setAttribute('aria-selected',String(selected));document.querySelector('#tab-panel-'+tab).hidden=!selected}document.querySelector('#tab-'+name).focus();if(name==='history')loadBidHistory()}
for(const tab of ['analysis','history','library'])document.querySelector('#tab-'+tab).onclick=()=>setTab(tab);
reviewButton.onclick=()=>{if(latest.length&&!tagDialog.open)tagDialog.showModal()};
document.querySelector('#close-tags').onclick=()=>tagDialog.close();
tagDialog.onclick=event=>{if(event.target===tagDialog)tagDialog.close()};
tagDialog.onclose=hideTagPreview;
async function readChunkResponse(response){
  const contentType=response.headers.get('Content-Type')||'';
  if(!contentType.includes('application/json')){
    if(response.status>=500)throw Error(`Máy chủ tạm ngắt khi xử lý (HTTP ${response.status}). Hãy thử lại sau ít phút.`);
    throw Error(`Máy chủ trả phản hồi không hợp lệ (HTTP ${response.status}).`);
  }
  const data=await response.json();
  if(!response.ok)throw Error(data.error||`Phân tích thất bại (HTTP ${response.status}).`);
  return data;
}
async function analyzeFile(file,semantic,threshold){
  const query='?filename='+encodeURIComponent(file.name)+'&semantic='+semantic+'&threshold='+encodeURIComponent(threshold);
  appendProcessingLog('running',`Đang tải lên ${file.name}`);
  const started=await readChunkResponse(await fetch('/api/chunk-job'+query,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file}));
  if(!started.id)throw Error('Máy chủ không tạo được phiên phân tích.');
  appendProcessingLog('queued',`${file.name}: Đã nhận file, đang chờ phân tích`);
  const deadline=Date.now()+15*60*1000;
  let lastPhase='';
  while(Date.now()<deadline){
    await new Promise(resolve=>setTimeout(resolve,1500));
    const job=await readChunkResponse(await fetch('/api/chunk-job?id='+encodeURIComponent(started.id)));
    if(job.phase&&job.phase!==lastPhase){appendProcessingLog(job.status==='error'?'error':job.status==='done'?'done':'running',`${file.name}: ${job.phase}`);lastPhase=job.phase}
    if(job.status==='done')return job.result;
    if(job.status==='error')throw Error(job.error||'Phân tích thất bại.');
    if(job.status!=='queued'&&job.status!=='running')throw Error('Trạng thái phân tích không hợp lệ.');
  }
  throw Error('Phân tích quá 15 phút. Hãy thử lại sau.');
}
function nextStepTags(){return [...new Set(latest.flatMap(doc=>doc.chunks.map(chunk=>chunk.labels.topics[0]).filter(Boolean)))]}
function renderCandidates(){const groups=new Map();for(const doc of latest)for(const chunk of doc.chunks)for(const topic of chunk.labels.topics){if(!groups.has(topic))groups.set(topic,[]);groups.get(topic).push(chunk)}candidateBox.replaceChildren();candidateBox.hidden=!latest.length;reviewButton.hidden=!latest.length;updateOverview();if(!latest.length)return;candidateBox.append(el('p','hint','Tất cả tag đều được dùng ở bước tiếp theo. Rê chuột vào tag để xem nội dung đoạn.'));candidateBox.append(el('h3','',`Tất cả tag (${groups.size})`));const list=el('div','candidate-list');for(const [topic,chunks] of groups){const chip=el('span','tag-chip approved',topic);chip.tabIndex=0;chip.onpointerenter=event=>showTagPreview(chip,topic,chunks,event);chip.onpointermove=event=>showTagPreview(chip,topic,chunks,event);chip.onpointerleave=hideTagPreview;chip.onfocus=()=>showTagPreview(chip,topic,chunks);chip.onblur=hideTagPreview;list.append(chip)}candidateBox.append(list);candidateBox.append(el('p','meta',`Đi tiếp: ${nextStepTags().length} tag`))}
document.querySelector('#run').onclick=async()=>{
 analysisRevision++;suggestionGeneration++;suggestionAbortController?.abort();reportGeneration++;activeSuggestionKey='';lastSuggestionKey='';clearTimeout(suggestionTimer);
 clearTimeout(bidSaveTimer);latest=[];latestMatch=null;latestReport=null;activeBidId=null;reportOverrides.clear();
 document.querySelector('#report-content').replaceChildren();reportToolbar.hidden=true;document.querySelector('#report-run').disabled=true;document.querySelector('#report-print').hidden=true;
 compareResults.replaceChildren();compareStatus.textContent='';status.textContent='';status.className='';reportStatus.textContent='';
 candidateBox.hidden=true;compareBox.hidden=true;reviewButton.hidden=true;exportBtn.disabled=true;hideProcessingFiles();clearProcessingLog();
 const selected=[...files.files];if(!selected.length){status.textContent='Hãy chọn PDF hoặc DOCX.';return}
 activeBidTitle=selected.map(file=>file.name).join(' · ').slice(0,255);
 showProcessingFiles(selected.map(file=>file.name));startRun('Phân tích & tổng hợp');
 const button=document.querySelector('#run'),semantic=document.querySelector('#semantic').checked,threshold=document.querySelector('#threshold').value;
 button.disabled=true;files.disabled=true;let errors=[];
 try{
  const created=await fetch('/api/bids',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:activeBidTitle})});
  const createdData=await created.json();if(!created.ok)throw Error(createdData.error||'Không lưu được bid vào lịch sử');activeBidId=createdData.bid.id;
  const results=await Promise.allSettled(selected.map(file=>analyzeFile(file,semantic,threshold)));
  for(const [index,result] of results.entries()){
   if(result.status==='fulfilled')latest.push(result.value);
   else{const message=result.reason?.message||String(result.reason);errors.push(`${selected[index].name}: ${message}`);appendProcessingLog('error',`${selected[index].name}: ${message}`)}
  }
  if(latest.length)renderCandidates();
  await saveBidSnapshot(latest.length?(errors.length?'partial':'processing'):'error');
  exportBtn.disabled=!latest.length;status.textContent=errors.length?'Lỗi: '+errors.join('; '):'';status.className=errors.length?'error':'';
  if(latest.length){setTab('analysis');await loadModelStatus();if(llmReady)generateBidReport();else{hideProcessingFiles();reportStatus.textContent='Chưa kết nối model để tạo bản tổng hợp.';finishRun('Chưa kết nối model')}}else{hideProcessingFiles();reportStatus.textContent='Không phân tích được tài liệu.';finishRun('Không phân tích được tài liệu')}
 }catch(error){hideProcessingFiles();status.className='error';status.textContent='Không lưu được bid: '+error.message;finishRun('Không lưu được bid')}
 finally{files.disabled=false;updateRunButton()}
};
function renderLibrary(){
 libraryList.replaceChildren();
 if(!library.length){libraryList.append(el('p','meta','Chưa có file trong thư viện.'));return}
 for(const file of library){
  const row=el('div','library-file'),head=el('div','library-file-head'),remove=el('button','library-delete','Xóa');
  remove.type='button';remove.setAttribute('aria-label',`Xóa tài liệu ${file.filename}`);
  remove.onclick=async()=>{
   if(!window.confirm(`Xóa “${file.filename}” khỏi thư viện?`))return;
   remove.disabled=true;
   try{
    const response=await fetch('/api/library?id='+encodeURIComponent(file.id),{method:'DELETE'});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Không xóa được tài liệu');
    library=library.filter(entry=>entry.id!==file.id);
    for(const item of latestMatch?.tag_matches||[]){item.suggestions=(item.suggestions||[]).filter(entry=>entry.file_id!==file.id);item.manual_files=(item.manual_files||[]).filter(entry=>entry.file_id!==file.id);item.selected_file_ids=(item.selected_file_ids||[]).filter(id=>id!==file.id)}
    for(const item of latestReport?.requirements||[])item.file_ids=(item.file_ids||[]).filter(id=>id!==file.id);
    for(const edit of reportOverrides.values())edit.file_ids=edit.file_ids.filter(id=>id!==file.id);
    renderLibrary();updateOverview();if(latestMatch)renderTagResults(latestMatch.tag_matches||[]);if(latestReport)renderBidReport();scheduleBidSave();
    libraryStatus.className='';libraryStatus.textContent=`Đã xóa ${file.filename} khỏi thư viện.`;
   }catch(error){libraryStatus.className='error';libraryStatus.textContent='Lỗi: '+error.message;remove.disabled=false}
  };
  head.append(el('strong','',file.filename),remove);row.append(head);
  const details=el('details'),summary=el('summary','','Tóm tắt nội dung tài liệu');details.append(summary);
  const textarea=el('textarea');textarea.value=file.description_md;textarea.setAttribute('aria-label',`Tóm tắt nội dung ${file.filename}`);
  const save=el('button','secondary','Lưu tóm tắt');save.onclick=async()=>{save.disabled=true;try{const response=await fetch('/api/library-description',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:file.id,description_md:textarea.value})});const data=await response.json();if(!response.ok)throw Error(data.error||'Không lưu được tóm tắt');file.description_md=textarea.value;libraryStatus.textContent=`Đã lưu tóm tắt cho ${file.filename}.`}catch(error){libraryStatus.textContent='Lỗi: '+error.message}finally{save.disabled=false}};
  details.append(textarea,save);row.append(details);libraryList.append(row)
 }
}
async function saveLibraryFiles(filesToSave,onSaved){let saved=0,errors=[];for(const [index,file] of filesToSave.entries()){libraryStatus.textContent=`Đang lưu ${index+1}/${filesToSave.length}: ${file.name}`;try{const response=await fetch('/api/library?filename='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});const data=await response.json();if(!response.ok)throw Error(data.error||'Không lưu được file');saved++;if(onSaved)onSaved(data.file)}catch(error){errors.push(`${file.name}: ${error.message}`)}}await loadLibrary();if(latestReport)renderBidReport();libraryStatus.textContent=`Đã lưu ${saved}/${filesToSave.length} file và tạo tóm tắt riêng.`+(errors.length?' Lỗi: '+errors.join('; '):'');libraryStatus.className=errors.length?'error':'';return {saved,errors}}
function renderTagResults(){
 // Match results remain available to the report; the per-tag suggestion list is hidden.
 compareResults.replaceChildren();
 compareBox.hidden=true;
}
async function loadModelStatus(){try{const response=await fetch('/api/llm-status');const data=await response.json();llmReady=Boolean(data.ready)}catch(error){llmReady=false;if(latest.length)reportStatus.textContent='Không kiểm tra được trạng thái model.'}}
async function loadLibrary(){try{const response=await fetch('/api/library');const data=await response.json();if(!response.ok)throw Error(data.error||'Không tải được thư viện');library=data.files;renderLibrary();updateOverview()}catch(error){libraryStatus.textContent='Lỗi: '+error.message}}
document.querySelector('#library-save').onclick=async()=>{const selected=[...libraryUpload.files];if(!selected.length){libraryStatus.textContent='Hãy chọn PDF hoặc DOCX.';return}const button=document.querySelector('#library-save');button.disabled=true;try{await saveLibraryFiles(selected);libraryUpload.value=''}finally{button.disabled=false}};
const reportBox=document.querySelector('#report-content'),reportStatus=document.querySelector('#report-status'),reportRun=document.querySelector('#report-run'),reportPrint=document.querySelector('#report-print'),reportToolbar=document.querySelector('#report-toolbar');
let reportGeneration=0;const reportOverrides=new Map();function reportKey(item){return [item.tag,item.title].join("||")}function rememberReportEdit(item){reportOverrides.set(reportKey(item),{file_ids:[...(item.file_ids||[])]});scheduleBidSave()}
function sourceDetails(ids){return reportSourceTags(ids)}
const reportSourcePreview=document.querySelector('#report-source-preview');let sourcePreviewHideTimer=null;
function hideReportSourcePreview(){clearTimeout(sourcePreviewHideTimer);reportSourcePreview.hidden=true}
function scheduleHideReportSourcePreview(){clearTimeout(sourcePreviewHideTimer);sourcePreviewHideTimer=setTimeout(hideReportSourcePreview,150)}
reportSourcePreview.onpointerenter=()=>clearTimeout(sourcePreviewHideTimer);reportSourcePreview.onpointerleave=hideReportSourcePreview;
function sourceTableRows(block){
 if(Array.isArray(block.rows)&&block.rows.length)return block.rows;
 const lines=String(block.text||'').split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
 if(lines.length<2||!lines.every(line=>line.includes('|')))return null;
 const rows=lines.map(line=>line.replace(/^\||\|$/g,'').split('|').map(cell=>cell.trim()));
 const width=Math.max(...rows.map(row=>row.length));
 return width>=2?rows.map(row=>[...row,...Array(width-row.length).fill('')]):null;
}
function appendSourceTable(section,rows){
 const scroll=el('div','report-source-table-scroll'),table=el('table','report-source-table'),body=el('tbody');
 for(const row of rows){const tr=el('tr');for(const cell of row)tr.append(el('td','',String(cell??'')));body.append(tr)}
 table.append(body);scroll.append(table);section.append(scroll);
}
function sourcePreviewChunk(chunk){
 const section=el('section','report-source-chunk');
 section.append(el('div','report-source-meta',`${chunk.file||'Tài liệu'}${chunk.pages?.length?' · trang '+chunk.pages.join(', '):''}`));
 if(!chunk.blocks?.length){const rows=sourceTableRows({text:chunk.text});if(rows)appendSourceTable(section,rows);else section.append(el('p','report-source-text',chunk.text||''));return section}
 for(const block of chunk.blocks){
  const rows=block.kind==='table'?sourceTableRows(block):null;
  if(rows)appendSourceTable(section,rows);
  else if(block.text)section.append(el('p','report-source-text',block.text));
 }
 return section;
}
function showReportSourcePreview(chip,topic,chunks){clearTimeout(sourcePreviewHideTimer);reportSourcePreview.replaceChildren(el('strong','',topic),...chunks.map(sourcePreviewChunk));reportSourcePreview.hidden=false;const rect=chip.getBoundingClientRect();reportSourcePreview.style.left=Math.max(12,Math.min(rect.left,innerWidth-reportSourcePreview.offsetWidth-12))+'px';reportSourcePreview.style.top=Math.max(12,Math.min(rect.bottom+8,innerHeight-reportSourcePreview.offsetHeight-12))+'px'}
function reportSourceTags(ids){const wanted=new Set(ids),groups=new Map();for(const chunk of latest.flatMap(doc=>doc.chunks)){if(!wanted.has(chunk.id))continue;const topics=chunk.labels?.topics?.length?chunk.labels.topics:[chunk.section_path?.at(-1)||chunk.file||'Nguồn'];for(const topic of topics){if(!groups.has(topic))groups.set(topic,[]);if(!groups.get(topic).some(item=>item.id===chunk.id))groups.get(topic).push(chunk)}}if(!groups.size)return null;const wrap=el('div','report-source-tags');for(const [topic,chunks] of groups){const chip=el('button','report-source-tag',topic+(chunks.length>1?` · ${chunks.length}`:''));chip.type='button';chip.setAttribute('aria-label',`Xem nguồn: ${topic}`);chip.onpointerenter=()=>showReportSourcePreview(chip,topic,chunks);chip.onpointerleave=scheduleHideReportSourcePreview;chip.onfocus=()=>showReportSourcePreview(chip,topic,chunks);chip.onblur=scheduleHideReportSourcePreview;chip.onclick=()=>showReportSourcePreview(chip,topic,chunks);wrap.append(chip)}return wrap}
function reportSection(title){const section=el('section','report-section');section.append(el('h2','',title));reportBox.append(section);return section}
function numberedSection(parent,number,title){const section=el('div','report-subsection');const heading=el('h3');heading.append(el('span','report-number',number+'.'),document.createTextNode(title));section.append(heading);parent.append(section);return section}
function deadlineStatus(value){
 const text=String(value||''),dayFirst=text.match(/(?:^|\D)(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})(?!\d)/),iso=text.match(/(?:^|\D)(\d{4})-(\d{2})-(\d{2})(?!\d)/);
 const now=new Date();let day,month,year;
 if(dayFirst){day=Number(dayFirst[1]);month=Number(dayFirst[2]);year=Number(dayFirst[3])}
 else if(iso){year=Number(iso[1]);month=Number(iso[2]);day=Number(iso[3])}
 else{
  const dayMonth=text.match(/(?:^|\D)(\d{1,2})[\/.-](\d{1,2})(?![\/.-]\d)(?!\d)/);
  if(dayMonth)return ['Ngày / tháng','unknown'];
  const monthOnly=text.match(/(?:^|\D)(\d{1,2})[\/.-](\d{4})(?!\d)/)||text.match(/tháng\s+(\d{1,2})\s*(?:năm|[\/.-])\s*(\d{4})/i);
  if(!monthOnly)return ['Theo mốc','unknown'];
  month=Number(monthOnly[1]);year=Number(monthOnly[2]);if(month<1||month>12)return ['Chưa rõ tháng','unknown'];
  const monthIndex=year*12+month,currentIndex=now.getFullYear()*12+now.getMonth()+1;
  return monthIndex<currentIndex?['Đã qua','past']:monthIndex>currentIndex?['Sắp tới','upcoming']:['Tháng này','today'];
 }
 const date=new Date(year,month-1,day);
 if(date.getFullYear()!==year||date.getMonth()!==month-1||date.getDate()!==day)return ['Chưa rõ ngày','unknown'];
 const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
 return date<today?['Đã qua','past']:date>today?['Sắp tới','upcoming']:['Hôm nay','today']
}
function milestoneDateText(value){const text=String(value||'').replace(/\s+at\s+/i,', '),full=text.match(/^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})(.*)$/),partial=text.match(/^(\d{1,2})[\/.-](\d{1,2})(?![\/.-]\d)(.*)$/),monthOnly=text.match(/^(\d{1,2})[\/.-](\d{4})$/);const wrap=el('strong','report-date-value');if(full){const dateLine=el('span','report-date-line');dateLine.append(el('span','report-date-primary',`${full[1].padStart(2,'0')}/${full[2].padStart(2,'0')}`),el('span','report-date-year',full[3]));wrap.append(dateLine);const time=full[4].replace(/^[\s,]+/,'').trim();if(time)wrap.append(el('span','report-date-secondary',time))}else if(partial){wrap.append(el('span','report-date-primary',`${partial[1].padStart(2,'0')}/${partial[2].padStart(2,'0')}`));if(partial[3])wrap.append(el('span','report-date-secondary',partial[3]))}else if(monthOnly){wrap.append(el('span','report-date-primary',`Tháng ${Number(monthOnly[1])}`),el('span','report-date-secondary',monthOnly[2]))}else wrap.textContent=text;return wrap}
function renderBidReport(){
 reportBox.replaceChildren();if(!latestReport)return;const r=latestReport;
 const hero=el('header','report-hero');hero.append(el('p','eyebrow','TỔNG QUAN BID'),el('h1','',r.title||'Hồ sơ thầu'));
 if(r.buyer){const meta=el('div','report-meta'),item=el('div','report-meta-item');item.append(el('span','','BÊN MỞ THẦU'),el('strong','',r.buyer));meta.append(item);hero.append(meta)}
 if(r.overview)hero.append(el('p','report-overview',r.overview));reportBox.append(hero);
 const scope=reportSection('Phạm vi công việc'),scopeGrid=el('div','report-scope-grid');scope.append(scopeGrid);
 for(const [index,key,title] of [[1,'objective','Mục tiêu chính của project'],[2,'arrangement','Hình thức hợp đồng'],[3,'content_provider','Ai cung cấp nội dung chuyên môn'],[4,'bid_submission_method','Hình thức nộp thầu']]){const item=r.scope?.[key]||{},part=numberedSection(scopeGrid,index,title);if(key==='objective'&&item.detail){const lines=item.detail.split(/\n+|(?:^|\s)[-•]\s+/).map(l=>l.replace(/^\s*[-•*]\s*/,'').trim()).filter(Boolean);if(lines.length>1){const list=el('ul','report-objective-list');for(const line of lines)list.append(el('li','',line));part.append(list)}else part.append(el('p','',item.detail))}else part.append(el('p','',item.detail||'Hồ sơ không nêu rõ.'));const source=sourceDetails(item.source_chunk_ids||[]);if(source)part.append(source)}
 const evaluation=el('section','report-subsection report-evaluation'),evaluationTitle=el('h3'),evaluationData=r.evaluation_method||{},allRules=evaluationData.rules||[],eligibilityRules=allRules.filter(x=>x.kind==='eligibility'),evaluationRules=allRules.filter(x=>x.kind!=='eligibility');
 if(eligibilityRules.length){const box=el('section','report-subsection report-eligibility'),list=el('ul','report-objective-list');box.append(el('h3','','Điều kiện tham gia bid'));for(const rule of eligibilityRules){const li=el('li','',rule.detail);const src=reportSourceTags(rule.source_chunk_ids||[]);if(src)li.append(src);list.append(li)}box.append(list);scope.insertBefore(box,scope.firstChild)}
 evaluationTitle.append(el('span','report-number','5.'),document.createTextNode('Cách chấm điểm và đánh giá hồ sơ'));evaluation.append(evaluationTitle);scopeGrid.append(evaluation);
 const scoringRules=evaluationRules.filter(rule=>rule.kind==='scoring'||(rule.kind==='evaluation'&&/\d|%|công thức|tỷ trọng|thang điểm/i.test(rule.detail||''))),otherRules=evaluationRules.filter(rule=>!scoringRules.includes(rule));
 const weightedCriteria=(evaluationData.criteria||[]).filter(item=>item.weight?.trim()),otherCriteria=(evaluationData.criteria||[]).filter(item=>!item.weight?.trim());
 if(scoringRules.length||weightedCriteria.length){evaluation.append(el('h4','','Cách tính điểm'));const table=el('table','report-table'),head=el('tr');for(const title of ['Tiêu chí / nội dung','Điểm / tỷ trọng','Cách tính / đánh giá'])head.append(el('th','',title));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');for(const rule of scoringRules){const row=el('tr');row.append(el('td','','Quy tắc tính điểm'),el('td','','—'),el('td','',rule.detail));body.append(row)}for(const criterion of weightedCriteria){const row=el('tr');row.append(el('td','',criterion.name),el('td','',criterion.weight),el('td','',criterion.detail||''));body.append(row)}table.append(body);evaluation.append(table)}
 if(otherRules.length||otherCriteria.length||evaluationData.detail){const details=el('details','report-evaluation-other');details.append(el('summary','','Thông tin đánh giá khác'));const list=el('ul','report-evaluation-rules');if(evaluationData.detail)list.append(el('li','',evaluationData.detail));for(const rule of otherRules)list.append(el('li','',rule.detail));for(const criterion of otherCriteria)list.append(el('li','',criterion.name+(criterion.detail?': '+criterion.detail:'')));details.append(list);evaluation.append(details)}
 if(!evaluationRules.length&&!evaluationData.detail&&!evaluationData.criteria?.length)evaluation.append(el('p','','Hồ sơ không nêu rõ.'));const evaluationSourceIds=[...new Set([...(evaluationData.source_chunk_ids||[]),...evaluationRules.flatMap(rule=>rule.source_chunk_ids||[]),...(evaluationData.criteria||[]).flatMap(criterion=>criterion.source_chunk_ids||[])])];const evaluationSource=reportSourceTags(evaluationSourceIds);if(evaluationSource)evaluation.append(evaluationSource);
 const vendorWork=numberedSection(scope,6,'Chi tiết và khối lượng công việc');if(r.scope_table?.length){const table=el('table','report-table'),thead=el('thead'),row=el('tr');for(const title of ['Hạng mục công việc','Khối lượng','Chi tiết từ hồ sơ'])row.append(el('th','',title));thead.append(row);table.append(thead);const body=el('tbody');for(const item of r.scope_table){const tr=el('tr'),detail=el('td','',item.detail||'');const source=sourceDetails(item.source_chunk_ids||[]);if(source)detail.append(source);tr.append(el('td','',item.item),el('td','',item.quantity||'Không nêu'),detail);body.append(tr)}table.append(body);vendorWork.append(table)}else vendorWork.append(el('p','report-note','Hồ sơ không nêu rõ.'));

 if(r.clarification_questions?.length){const questions=reportSection('Câu hỏi nháp');const list=el('ul','report-questions');for(const question of r.clarification_questions)list.append(el('li','',question));questions.append(list)}
 const submission=reportSection('Tài liệu cần nộp');
 const timeline=numberedSection(submission,1,'Các mốc');{const deadlines=r.deadlines||[],fixed=!deadlines.length||deadlines.some(d=>d.kind),grid=el('div','report-date-grid');const slots=fixed?[['submission','Hạn nộp hồ sơ thầu'],['questions_due','Hạn gửi câu hỏi'],['answers_due','Hạn khách trả lời câu hỏi']].map(([kind,label])=>deadlines.find(d=>d.kind===kind)||{label,missing:true}):deadlines;for(const date of slots){const card=el('article','report-date'),head=el('div','report-date-head');if(date.missing){head.append(el('span','',date.label),el('span','report-date-status unknown','Chưa rõ'));card.append(head,el('p','report-note','Hồ sơ không nêu rõ.'));grid.append(card);continue}const [statusText,statusClass]=date.conditional?['Theo điều kiện','unknown']:deadlineStatus(date.value),dateText=milestoneDateText(date.value);head.append(el('span','',date.label),el('span','report-date-status '+statusClass,statusText));card.append(head,dateText);if(date.note)card.append(el('p','',date.note));const source=sourceDetails(date.source_chunk_ids||[]);if(source)card.append(source);grid.append(card)}timeline.append(grid)}
 const checklist=numberedSection(submission,2,'Yêu cầu hồ sơ');checklist.classList.add('report-checklist-section');const items=r.requirements||[];const categoryGrid=el('div','report-category-grid');checklist.append(categoryGrid);
 for(const category of ['Hồ sơ công ty','Proposal']){
  const categoryItems=items.filter(item=>item.category===category);
  const panel=el('section','report-category-panel'),heading=el('div','report-category-head');heading.append(el('h4','',category),el('span','',String(categoryItems.length)));panel.append(heading);categoryGrid.append(panel);
  if(!categoryItems.length)panel.append(el('p','report-empty','Chưa tìm thấy tài liệu cần nộp trong nhóm này.'));
  const group=el('div','report-checklist');
  for(const item of categoryItems){
   const row=el('article','report-check-row'),head=el('div','report-check-row-head'),rowKey=reportKey(item);row.dataset.reportKey=rowKey;
   head.append(el('h4','',item.title));
   const selected=library.filter(file=>(item.file_ids||[]).includes(file.id));
   head.append(el('span','report-status-tag '+(selected.length?'has-file':'missing-file'),selected.length?'Đã có':'Thiếu'));row.append(head);
   if(selected.length)row.append(el('div','report-file-summary','File đã chọn: '+selected.slice(0,2).map(file=>file.filename).join(' · ')+(selected.length>2?` · +${selected.length-2} file`:'')));
   const detail=el('details','report-item-details');detail.append(el('summary','','Chọn file liên quan'));
   const body=el('div','report-item-body');
   const options=el('div','report-file-options');
   for(const file of library){
    const label=el('label'),input=el('input');input.type='checkbox';input.checked=(item.file_ids||[]).includes(file.id);
    input.onchange=()=>{item.file_ids=input.checked?[...new Set([...(item.file_ids||[]),file.id])]:item.file_ids.filter(id=>id!==file.id);rememberReportEdit(item);renderBidReport();const current=[...document.querySelectorAll('.report-check-row')].find(entry=>entry.dataset.reportKey===rowKey);if(current)current.querySelector('.report-item-details').open=true};
    label.append(input,document.createTextNode(file.filename));options.append(label)
   }
   if(!library.length)options.append(el('p','report-note','Thư viện chưa có file.'));body.append(options);
   const source=sourceDetails(item.source_chunk_ids||[]);if(source)body.append(source);
   detail.append(body);row.append(detail);group.append(row)
  }
  panel.append(group)
 }

 reportPrint.hidden=false;reportRun.disabled=false;reportToolbar.hidden=false
}
async function reportJobResult(){
 const startedResponse=await fetch('/api/bid-report-job',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({documents:latest,matches:[]})});
 const started=await startedResponse.json();
 if(!startedResponse.ok)throw Error(started.error||'Không khởi tạo được báo cáo');
 appendProcessingLog('queued','Đã gửi tài liệu tới máy chủ để tạo báo cáo');
 const deadline=Date.now()+20*60*1000;
 let seen=0;
 while(Date.now()<deadline){
  await new Promise(resolve=>setTimeout(resolve,1500));
  const response=await fetch('/api/bid-report-job?id='+encodeURIComponent(started.id));
  const job=await response.json();
  if(!response.ok)throw Error(job.error||'Không đọc được tiến độ báo cáo');
  for(const event of (job.events||[]).slice(seen))appendProcessingLog(event.state,event.message);
  seen=(job.events||[]).length;
  if(job.status==='done')return job.result;
  if(job.status==='error')throw Error(job.error||'Không tạo được bản tổng hợp');
  if(job.status!=='queued'&&job.status!=='running')throw Error('Trạng thái báo cáo không hợp lệ');
 }
 throw Error('Tạo báo cáo quá 20 phút. Hãy thử lại sau.');
}
async function generateBidReport(){
 if(!latest.some(doc=>doc.chunks.length)||!llmReady)return;
 const runId=ensureRun('Tạo lại bản tổng hợp'),generation=++reportGeneration;
 reportRun.disabled=true;reportToolbar.hidden=true;reportStatus.className='meta';reportStatus.textContent='';
 showProcessingFiles(undefined,'Đang tạo bản tổng hợp');compareBox.hidden=true;
 try{
  const data=await reportJobResult();
  if(generation!==reportGeneration)return;
  for(const usage of data.usage_events||[data.usage])addRunUsage(usage,runId);
  if(data.usage_missing&&activeRun?.id===runId)activeRun.unknownCost=true;
  for(const item of data.requirements||[]){const edit=reportOverrides.get(reportKey(item));if(edit)item.file_ids=edit.file_ids.filter(id=>library.some(file=>file.id===id))}
  latestReport=data;renderBidReport();hideProcessingFiles();compareBox.hidden=true;reportStatus.textContent='';
  try{await saveBidSnapshot('complete');appendProcessingLog('done','Đã lưu bản tổng hợp vào lịch sử')}
  catch(saveError){reportStatus.className='error';reportStatus.textContent='Bản tổng hợp đã tạo nhưng chưa lưu được vào lịch sử: '+saveError.message;appendProcessingLog('error',reportStatus.textContent)}
  if(activeRun?.id===runId)finishRun('Hoàn tất');
 }catch(error){
  if(generation!==reportGeneration)return;
  reportStatus.className='error';reportStatus.textContent='Lỗi tạo bản tổng hợp: '+error.message;
  appendProcessingLog('error',reportStatus.textContent);
  hideProcessingFiles();compareBox.hidden=true;reportToolbar.hidden=!latestReport;
  if(activeRun?.id===runId){activeRun.unknownCost=true;finishRun('Lỗi tạo bản tổng hợp')}
 }finally{if(generation===reportGeneration)reportRun.disabled=false}
}
reportRun.onclick=generateBidReport;reportPrint.onclick=()=>window.print();
window.addEventListener('beforeprint',()=>{const evaluation=document.querySelector('.report-evaluation-other');if(evaluation&&!evaluation.open){evaluation.open=true;evaluation.dataset.printOpened='true'}});
window.addEventListener('afterprint',()=>{const evaluation=document.querySelector('.report-evaluation-other[data-print-opened]');if(evaluation){evaluation.open=false;delete evaluation.dataset.printOpened}});
compareRetry.onclick=null;
loadLibrary();loadModelStatus();
exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify({schema_version:10,next_step_tags:nextStepTags(),documents:latest,file_suggestions:latestMatch,bid_report:latestReport,run_metrics:runHistory.map(run=>({label:run.label,duration_seconds:Number(metricDuration(run).split(' ')[0]),input_tokens:run.inputTokens,output_tokens:run.outputTokens,estimated_cost_usd:run.unknownCost?null:run.costUsd,api_calls:run.calls,note:run.note}))},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='suggested_files.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
