
const files=document.querySelector('#files'), status=document.querySelector('#status'), candidateBox=document.querySelector('#candidates'), exportBtn=document.querySelector('#export'),compareBox=document.querySelector('#compare'),compareRetry=document.querySelector('#compare-retry'),compareStatus=document.querySelector('#compare-status'),compareResults=document.querySelector('#compare-results'),libraryUpload=document.querySelector('#library-upload'),libraryStatus=document.querySelector('#library-status'),libraryList=document.querySelector('#library-list');let latest=[],latestMatch=null,latestReport=null,library=[],llmReady=false,analysisRevision=0,suggestionGeneration=0,suggestionTimer=null,suggestionAbortController=null,lastSuggestionKey='',activeSuggestionKey='';const tagPreview=document.querySelector('#tag-preview'),tagDialog=document.querySelector('#tag-dialog'),reviewButton=document.querySelector('#review-tags');function updateOverview(){document.querySelector('#metric-documents').textContent=latest.length;document.querySelector('#metric-tags').textContent=nextStepTags().length;document.querySelector('#metric-library').textContent=library.length}
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
const processingFiles=document.querySelector('#processing-files');function showProcessingFiles(names,phase='Đang phân tích'){const filesToShow=names?.length?names:latest.map(doc=>doc.file).filter(Boolean);processingFiles.textContent=phase+(filesToShow.length?': '+filesToShow.join(' · '):'…');processingFiles.hidden=false}function hideProcessingFiles(){processingFiles.hidden=true;processingFiles.textContent=''}
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
function setTab(name){for(const tab of ['analysis','library']){const selected=tab===name;document.querySelector('#tab-'+tab).setAttribute('aria-selected',String(selected));document.querySelector('#tab-panel-'+tab).hidden=!selected}document.querySelector('#tab-'+name).focus()}
for(const tab of ['analysis','library'])document.querySelector('#tab-'+tab).onclick=()=>setTab(tab);
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
  const started=await readChunkResponse(await fetch('/api/chunk-job'+query,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file}));
  if(!started.id)throw Error('Máy chủ không tạo được phiên phân tích.');
  const deadline=Date.now()+15*60*1000;
  while(Date.now()<deadline){
    await new Promise(resolve=>setTimeout(resolve,1500));
    const job=await readChunkResponse(await fetch('/api/chunk-job?id='+encodeURIComponent(started.id)));
    if(job.status==='done')return job.result;
    if(job.status==='error')throw Error(job.error||'Phân tích thất bại.');
    if(job.status!=='queued'&&job.status!=='running')throw Error('Trạng thái phân tích không hợp lệ.');
  }
  throw Error('Phân tích quá 15 phút. Hãy thử lại sau.');
}
function nextStepTags(){return [...new Set(latest.flatMap(doc=>doc.chunks.map(chunk=>chunk.labels.topics[0]).filter(Boolean)))]}
function renderCandidates(){const groups={approved:new Map(),reject:new Map()};for(const doc of latest)for(const chunk of doc.chunks)for(const topic of chunk.labels.topics){const tier=chunk.requirement_tier==='approved'?'approved':'reject',group=groups[tier];if(!group.has(topic))group.set(topic,[]);group.get(topic).push(chunk)}candidateBox.replaceChildren();candidateBox.hidden=!latest.length;reviewButton.hidden=!latest.length;updateOverview();if(!latest.length)return;candidateBox.append(el('p','hint','Mọi tag đều được xét ở bước tiếp theo. Rê chuột vào tag để xem nội dung đoạn.'));for(const tier of ['approved','reject']){const group=groups[tier];candidateBox.append(el('h3','',`${tier} (${group.size})`));const list=el('div','candidate-list');for(const [topic,chunks] of group){const chunk=chunks[0],chip=el('span','tag-chip '+tier,`${topic} · ${Number(chunk.requirement_score).toFixed(2)}`);chip.tabIndex=0;chip.onpointerenter=event=>showTagPreview(chip,topic,chunks,event);chip.onpointermove=event=>showTagPreview(chip,topic,chunks,event);chip.onpointerleave=hideTagPreview;chip.onfocus=()=>showTagPreview(chip,topic,chunks);chip.onblur=hideTagPreview;list.append(chip)}candidateBox.append(list)}candidateBox.append(el('p','meta',`Đi tiếp: ${nextStepTags().length} tag`))}
document.querySelector('#run').onclick=async()=>{
 analysisRevision++;suggestionGeneration++;suggestionAbortController?.abort();reportGeneration++;activeSuggestionKey='';lastSuggestionKey='';clearTimeout(suggestionTimer);
 latest=[];latestMatch=null;latestReport=null;reportOverrides.clear();
 document.querySelector('#report-content').replaceChildren();reportToolbar.hidden=true;document.querySelector('#report-run').disabled=true;document.querySelector('#report-print').hidden=true;
 compareResults.replaceChildren();compareStatus.textContent='';status.textContent='';status.className='';reportStatus.textContent='';
 candidateBox.hidden=true;compareBox.hidden=true;reviewButton.hidden=true;exportBtn.disabled=true;hideProcessingFiles();
 const selected=[...files.files];if(!selected.length){status.textContent='Hãy chọn PDF hoặc DOCX.';return}
 showProcessingFiles(selected.map(file=>file.name));startRun('Phân tích & tổng hợp');
 const button=document.querySelector('#run'),semantic=document.querySelector('#semantic').checked,threshold=document.querySelector('#threshold').value;
 button.disabled=true;files.disabled=true;let errors=[];
 try{
  for(const file of selected){try{const data=await analyzeFile(file,semantic,threshold);latest.push(data);renderCandidates()}catch(error){errors.push(`${file.name}: ${error.message}`)}}
  exportBtn.disabled=!latest.length;status.textContent=errors.length?'Lỗi: '+errors.join('; '):'';status.className=errors.length?'error':'';
  if(latest.length){setTab('analysis');scheduleSuggestions()}else{hideProcessingFiles();reportStatus.textContent='Không phân tích được tài liệu.';finishRun('Không phân tích được tài liệu')}
 }finally{files.disabled=false;updateRunButton()}
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
    if(activeSuggestionKey){suggestionGeneration++;suggestionAbortController?.abort();activeSuggestionKey='';lastSuggestionKey='';scheduleSuggestions()}
    renderLibrary();updateOverview();if(latestMatch)renderTagResults(latestMatch.tag_matches||[]);if(latestReport)renderBidReport();
    libraryStatus.className='';libraryStatus.textContent=`Đã xóa ${file.filename} khỏi thư viện.`;
   }catch(error){libraryStatus.className='error';libraryStatus.textContent='Lỗi: '+error.message;remove.disabled=false}
  };
  head.append(el('strong','',file.filename),remove);row.append(head);
  const details=el('details'),summary=el('summary','','Tóm tắt nội dung tài liệu');details.append(summary);
  const textarea=el('textarea');textarea.value=file.description_md;textarea.setAttribute('aria-label',`Tóm tắt nội dung ${file.filename}`);
  const save=el('button','secondary','Lưu tóm tắt');save.onclick=async()=>{save.disabled=true;try{const response=await fetch('/api/library-description',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:file.id,description_md:textarea.value})});const data=await response.json();if(!response.ok)throw Error(data.error||'Không lưu được tóm tắt');file.description_md=textarea.value;lastSuggestionKey='';scheduleSuggestions();libraryStatus.textContent=`Đã lưu tóm tắt cho ${file.filename}.`}catch(error){libraryStatus.textContent='Lỗi: '+error.message}finally{save.disabled=false}};
  details.append(textarea,save);row.append(details);libraryList.append(row)
 }
}
async function saveLibraryFiles(filesToSave,onSaved){let saved=0,errors=[];for(const [index,file] of filesToSave.entries()){libraryStatus.textContent=`Đang lưu ${index+1}/${filesToSave.length}: ${file.name}`;try{const response=await fetch('/api/library?filename='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});const data=await response.json();if(!response.ok)throw Error(data.error||'Không lưu được file');saved++;if(onSaved)onSaved(data.file)}catch(error){errors.push(`${file.name}: ${error.message}`)}}await loadLibrary();if(saved&&!onSaved){lastSuggestionKey='';scheduleSuggestions()}libraryStatus.textContent=`Đã lưu ${saved}/${filesToSave.length} file và tạo tóm tắt riêng.`+(errors.length?' Lỗi: '+errors.join('; '):'');libraryStatus.className=errors.length?'error':'';return {saved,errors}}
function renderTagResults(items){
 compareResults.replaceChildren();document.querySelector('#compare-heading').textContent=`File gợi ý theo tag (${items.length})`;
 for(const [index,item] of items.entries()){
  item.selected_file_ids??=[];item.manual_files??=[];const card=el('details','tag-result'),summary=el('summary');summary.append(el('strong','',item.tag),el('small','',`${item.suggestions.length} file gợi ý`));card.append(summary);const body=el('div','tag-result-body');
  const source=el('details');source.append(el('summary','','Xem nội dung tag'),el('pre','tag-text',item.full_text));body.append(source);if(item.text_sent_to_model_truncated)body.append(el('p','req-warning','Model chỉ nhận 30.000 ký tự đầu.'));
  const grid=el('div','suggestion-grid'),all=[...item.suggestions,...item.manual_files];if(!all.length)grid.append(el('p','empty-result','Chưa có file gợi ý. Bạn có thể thêm file từ thư viện hoặc tải lên.'));
  const selectedCount=el('p','selected-count',`Đã chọn ${item.selected_file_ids.length} file`);
  for(const suggestion of all){const row=el('label','suggestion select-suggestion'),check=el('input');check.type='checkbox';check.checked=item.selected_file_ids.includes(suggestion.file_id);check.setAttribute('aria-label',`Chọn ${suggestion.filename} cho tag ${item.tag}`);check.onchange=()=>{item.selected_file_ids=check.checked?[...new Set([...item.selected_file_ids,suggestion.file_id])]:item.selected_file_ids.filter(id=>id!==suggestion.file_id);selectedCount.textContent=`Đã chọn ${item.selected_file_ids.length} file`;if(latestReport)reportStatus.textContent='Bạn đã đổi file theo tag. Bấm “Tạo lại” để cập nhật bản tổng hợp.'};const info=el('span');info.append(el('strong','',suggestion.filename));if(suggestion.reason)info.append(el('span','suggestion-verdict',suggestion.reason));row.append(check,info);grid.append(row)}body.append(grid,selectedCount);
  const add=el('details','tag-details');add.append(el('summary','','Thêm file khác'));const addBody=el('div','add-file-body'),fromLibrary=el('div','controls'),picker=el('select');picker.setAttribute('aria-label',`Chọn file khác cho tag ${item.tag}`);picker.append(el('option','','Chọn từ thư viện'));picker.firstChild.value='';const used=new Set(all.map(file=>file.file_id));for(const file of library)if(!used.has(file.id)){const option=el('option','',file.filename);option.value=file.id;picker.append(option)}const addButton=el('button','secondary','Thêm file');addButton.onclick=()=>{const file=library.find(entry=>entry.id===picker.value);if(!file)return;item.manual_files.push({file_id:file.id,filename:file.filename,verdict:'manual',reason:''});item.selected_file_ids=[...new Set([...item.selected_file_ids,file.id])];renderTagResults(items);compareResults.querySelectorAll('.tag-result')[index].open=true};fromLibrary.append(picker,addButton);
  const uploadRow=el('div','controls'),upload=el('input'),uploadButton=el('button','secondary','Tải lên và chọn');upload.type='file';upload.accept='.pdf,.docx';upload.multiple=true;upload.setAttribute('aria-label',`Tải thêm file cho tag ${item.tag}`);uploadButton.onclick=async()=>{const filesToSave=[...upload.files];if(!filesToSave.length){compareStatus.textContent='Hãy chọn PDF hoặc DOCX để tải lên.';return}uploadButton.disabled=true;try{const result=await saveLibraryFiles(filesToSave,file=>{item.manual_files.push({file_id:file.id,filename:file.filename,verdict:'manual',reason:''});item.selected_file_ids=[...new Set([...item.selected_file_ids,file.id])]});compareStatus.textContent=`Đã thêm ${result.saved} file cho tag ${item.tag}.`;renderTagResults(items);compareResults.querySelectorAll('.tag-result')[index].open=true}finally{uploadButton.disabled=false}};uploadRow.append(upload,uploadButton);addBody.append(fromLibrary,uploadRow);add.append(addBody);body.append(add);card.append(body);compareResults.append(card)
 }
}
async function loadModelStatus(){try{const response=await fetch('/api/llm-status');const data=await response.json();llmReady=Boolean(data.ready);scheduleSuggestions()}catch(error){llmReady=false;if(latest.length)compareStatus.textContent='Không kiểm tra được trạng thái model.'}}
async function loadLibrary(){try{const response=await fetch('/api/library');const data=await response.json();if(!response.ok)throw Error(data.error||'Không tải được thư viện');library=data.files;renderLibrary();updateOverview()}catch(error){libraryStatus.textContent='Lỗi: '+error.message}}
document.querySelector('#library-save').onclick=async()=>{const selected=[...libraryUpload.files];if(!selected.length){libraryStatus.textContent='Hãy chọn PDF hoặc DOCX.';return}const button=document.querySelector('#library-save');button.disabled=true;try{await saveLibraryFiles(selected);libraryUpload.value=''}finally{button.disabled=false}};
function scheduleSuggestions(){clearTimeout(suggestionTimer);suggestionTimer=setTimeout(runAutoSuggestions,250)}
async function mapConcurrentOrdered(values,limit,task){
 const results=Array(values.length);let next=0;
 async function worker(){while(next<values.length){const index=next++;results[index]=await task(values[index],index)}}
 await Promise.all(Array.from({length:Math.min(limit,values.length)},worker));
 return results;
}
async function runAutoSuggestions(){
 if(!latest.length)return;
 const tags=nextStepTags();
 if(!tags.length){compareBox.hidden=true;compareResults.replaceChildren();latestMatch=null;if(latest.some(doc=>doc.chunks.length)&&llmReady)generateBidReport();else{hideProcessingFiles();reportStatus.textContent=latest.some(doc=>doc.chunks.length)?'Chưa kết nối model.':'Tài liệu không có nội dung để tạo bản tổng hợp.';finishRun('Không có nội dung để tổng hợp')}return}
 if(!library.length){compareBox.hidden=true;if(llmReady)generateBidReport();else{hideProcessingFiles();reportStatus.textContent='Chưa kết nối model.';finishRun('Chưa kết nối model')}return}
 if(!llmReady){compareBox.hidden=true;hideProcessingFiles();reportStatus.textContent='Chưa cấu hình model gợi ý trên máy chủ.';finishRun('Chưa kết nối model');return}
 const key=JSON.stringify([analysisRevision,tags,library.map(file=>[file.id,file.description_md])]);
 if(key===lastSuggestionKey||key===activeSuggestionKey)return;
 showProcessingFiles(undefined,'Đang gợi ý file');compareBox.hidden=true;ensureRun('Gợi ý file & tổng hợp');const generation=++suggestionGeneration;suggestionAbortController?.abort();const controller=new AbortController();suggestionAbortController=controller;activeSuggestionKey=key;compareRetry.hidden=true;compareStatus.className='';
 const allChunks=latest.flatMap(doc=>doc.chunks);
 const priorByTag=new Map((latestMatch?.tag_matches||[]).map(item=>[item.tag,item]));
 const runId=activeRun?.id;let completed=0;compareStatus.textContent=`Đang tự gợi ý 0/${tags.length} tag`;
 try{
  const items=await mapConcurrentOrdered(tags,10,async(tag)=>{
   const chunks=allChunks.filter(chunk=>chunk.labels.topics[0]===tag);
   const response=await fetch('/api/llm-match-tag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chunks}),signal:controller.signal});
   const data=await response.json();
   if(!response.ok)throw Error(data.error||'Model không gợi ý được');
   if(generation!==suggestionGeneration)return null;
   addRunUsage(data.usage,runId);const prior=priorByTag.get(tag);
   data.selected_file_ids=prior?.selected_file_ids?.filter(id=>library.some(file=>file.id===id))||[];
   data.manual_files=prior?.manual_files?.filter(file=>library.some(entry=>entry.id===file.file_id))||[];
   completed++;compareStatus.textContent=`Đang tự gợi ý ${completed}/${tags.length} tag`;
   return data;
  });
  if(generation!==suggestionGeneration)return;
  latestMatch={tag_matches:items};renderTagResults(items);
  lastSuggestionKey=key;compareStatus.textContent=`Đã tự gợi ý file cho ${items.length} tag. Hãy chọn file muốn dùng.`;generateBidReport();
 }catch(error){if(generation!==suggestionGeneration)return;controller.abort();compareStatus.textContent='Lỗi gợi ý: '+error.message;compareStatus.className='error';compareRetry.hidden=false;compareBox.hidden=false;reportStatus.className='error';reportStatus.textContent='Lỗi gợi ý file: '+error.message+' Hãy tải lại tài liệu để thử lại.';hideProcessingFiles();if(activeRun?.id===runId){activeRun.unknownCost=true;finishRun('Lỗi gợi ý file')}}
 finally{if(generation===suggestionGeneration)activeSuggestionKey='';if(suggestionAbortController===controller)suggestionAbortController=null}
}
const reportBox=document.querySelector('#report-content'),reportStatus=document.querySelector('#report-status'),reportRun=document.querySelector('#report-run'),reportPrint=document.querySelector('#report-print'),reportToolbar=document.querySelector('#report-toolbar');
let reportGeneration=0;const reportOverrides=new Map();function reportKey(item){return [item.tag,item.title].join("||")}function rememberReportEdit(item){reportOverrides.set(reportKey(item),{file_ids:[...(item.file_ids||[])]})}
function sourceDetails(ids){return reportSourceTags(ids)}
const reportSourcePreview=document.querySelector('#report-source-preview');let sourcePreviewHideTimer=null;
function hideReportSourcePreview(){clearTimeout(sourcePreviewHideTimer);reportSourcePreview.hidden=true}
function scheduleHideReportSourcePreview(){clearTimeout(sourcePreviewHideTimer);sourcePreviewHideTimer=setTimeout(hideReportSourcePreview,150)}
reportSourcePreview.onpointerenter=()=>clearTimeout(sourcePreviewHideTimer);reportSourcePreview.onpointerleave=hideReportSourcePreview;
function showReportSourcePreview(chip,topic,chunks){clearTimeout(sourcePreviewHideTimer);reportSourcePreview.replaceChildren(el('strong','',topic),el('span','',chunks.map(chunk=>`${chunk.file||'Tài liệu'}${chunk.pages?.length?' · trang '+chunk.pages.join(', '):''}\n${chunk.text||''}`).join('\n\n')));reportSourcePreview.hidden=false;const rect=chip.getBoundingClientRect();reportSourcePreview.style.left=Math.max(12,Math.min(rect.left,innerWidth-reportSourcePreview.offsetWidth-12))+'px';reportSourcePreview.style.top=Math.max(12,Math.min(rect.bottom+8,innerHeight-reportSourcePreview.offsetHeight-12))+'px'}
function reportSourceTags(ids){const wanted=new Set(ids),groups=new Map();for(const chunk of latest.flatMap(doc=>doc.chunks)){if(!wanted.has(chunk.id))continue;const topics=chunk.labels?.topics?.length?chunk.labels.topics:[chunk.section_path?.at(-1)||chunk.file||'Nguồn'];for(const topic of topics){if(!groups.has(topic))groups.set(topic,[]);if(!groups.get(topic).some(item=>item.id===chunk.id))groups.get(topic).push(chunk)}}if(!groups.size)return null;const wrap=el('div','report-source-tags');for(const [topic,chunks] of groups){const chip=el('button','report-source-tag',topic+(chunks.length>1?` · ${chunks.length}`:''));chip.type='button';chip.setAttribute('aria-label',`Xem nguồn: ${topic}`);chip.onpointerenter=()=>showReportSourcePreview(chip,topic,chunks);chip.onpointerleave=scheduleHideReportSourcePreview;chip.onfocus=()=>showReportSourcePreview(chip,topic,chunks);chip.onblur=scheduleHideReportSourcePreview;chip.onclick=()=>showReportSourcePreview(chip,topic,chunks);wrap.append(chip)}return wrap}
function reportSection(title){const section=el('section','report-section');section.append(el('h2','',title));reportBox.append(section);return section}
function numberedSection(parent,number,title){const section=el('div','report-subsection');const heading=el('h3');heading.append(el('span','report-number',number+'.'),document.createTextNode(title));section.append(heading);parent.append(section);return section}
function deadlineStatus(value){
 const text=String(value||''),dayFirst=text.match(/(?:^|\D)(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})(?!\d)/),iso=text.match(/(?:^|\D)(\d{4})-(\d{2})-(\d{2})(?!\d)/);
 const now=new Date();let day,month,year;
 if(dayFirst){day=Number(dayFirst[1]);month=Number(dayFirst[2]);year=Number(dayFirst[3])}
 else if(iso){year=Number(iso[1]);month=Number(iso[2]);day=Number(iso[3])}
 else{
  const monthOnly=text.match(/(?:^|\D)(\d{1,2})[\/.-](\d{4})(?!\d)/)||text.match(/tháng\s+(\d{1,2})\s*(?:năm|[\/.-])\s*(\d{4})/i);
  if(!monthOnly)return ['Chưa rõ năm','unknown'];
  month=Number(monthOnly[1]);year=Number(monthOnly[2]);if(month<1||month>12)return ['Chưa rõ tháng','unknown'];
  const monthIndex=year*12+month,currentIndex=now.getFullYear()*12+now.getMonth()+1;
  return monthIndex<currentIndex?['Đã qua','past']:monthIndex>currentIndex?['Sắp tới','upcoming']:['Tháng này','today'];
 }
 const date=new Date(year,month-1,day);
 if(date.getFullYear()!==year||date.getMonth()!==month-1||date.getDate()!==day)return ['Chưa rõ ngày','unknown'];
 const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
 return date<today?['Đã qua','past']:date>today?['Sắp tới','upcoming']:['Hôm nay','today']
}
function milestoneDateText(value){const text=String(value||''),monthOnly=text.match(/^(\d{1,2})[\/.-](\d{4})$/);return monthOnly?`Tháng ${Number(monthOnly[1])}/${monthOnly[2]}`:text.replace(/\s+at\s+/i,', ')}
function renderBidReport(){
 reportBox.replaceChildren();if(!latestReport)return;const r=latestReport;
 const hero=el('header','report-hero');hero.append(el('p','eyebrow','TỔNG QUAN BID'),el('h1','',r.title||'Hồ sơ thầu'));
 if(r.buyer){const meta=el('div','report-meta'),item=el('div','report-meta-item');item.append(el('span','','BÊN MỞ THẦU'),el('strong','',r.buyer));meta.append(item);hero.append(meta)}
 if(r.overview)hero.append(el('p','report-overview',r.overview));reportBox.append(hero);
 const scope=reportSection('Phạm vi công việc'),scopeGrid=el('div','report-scope-grid');scope.append(scopeGrid);
 for(const [index,key,title] of [[1,'objective','Mục tiêu chính của project'],[2,'arrangement','Hình thức'],[3,'content_provider','Ai cung cấp nội dung chuyên môn'],[4,'bid_submission_method','Hình thức nộp thầu']]){const item=r.scope?.[key]||{},part=numberedSection(scopeGrid,index,title);part.append(el('p','',item.detail||'Hồ sơ không nêu rõ.'));const source=sourceDetails(item.source_chunk_ids||[]);if(source)part.append(source)}
 const evaluation=el('details','report-subsection report-evaluation'),evaluationSummary=el('summary'),evaluationTitle=el('h3'),evaluationData=r.evaluation_method||{};evaluationTitle.append(el('span','report-number','5.'),document.createTextNode('Cách chấm điểm và đánh giá hồ sơ'));evaluationSummary.append(evaluationTitle);evaluation.append(evaluationSummary);scopeGrid.append(evaluation);if(evaluationData.rules?.length){const list=el('ul','report-evaluation-rules');for(const rule of evaluationData.rules)list.append(el('li','',rule.detail));evaluation.append(list)}else if(evaluationData.detail)evaluation.append(el('p','',evaluationData.detail));if(evaluationData.criteria?.length){const table=el('table','report-table'),head=el('tr');for(const title of ['Tiêu chí','Điểm / tỷ trọng','Cách đánh giá'])head.append(el('th','',title));const thead=el('thead');thead.append(head);table.append(thead);const body=el('tbody');for(const criterion of evaluationData.criteria){const row=el('tr');row.append(el('td','',criterion.name),el('td','',criterion.weight||'Không nêu'),el('td','',criterion.detail||''));body.append(row)}table.append(body);evaluation.append(table)}if(!evaluationData.rules?.length&&!evaluationData.detail&&!evaluationData.criteria?.length)evaluation.append(el('p','','Hồ sơ không nêu rõ.'));const evaluationSourceIds=[...new Set([...(evaluationData.source_chunk_ids||[]),...(evaluationData.rules||[]).flatMap(rule=>rule.source_chunk_ids||[]),...(evaluationData.criteria||[]).flatMap(criterion=>criterion.source_chunk_ids||[])])];const evaluationSource=reportSourceTags(evaluationSourceIds);if(evaluationSource)evaluation.append(evaluationSource);
 const vendorWork=numberedSection(scope,6,'Chi tiết và khối lượng công việc');if(r.scope_table?.length){const table=el('table','report-table'),thead=el('thead'),row=el('tr');for(const title of ['Hạng mục công việc','Khối lượng','Chi tiết từ hồ sơ'])row.append(el('th','',title));thead.append(row);table.append(thead);const body=el('tbody');for(const item of r.scope_table){const tr=el('tr'),detail=el('td','',item.detail||'');const source=sourceDetails(item.source_chunk_ids||[]);if(source)detail.append(source);tr.append(el('td','',item.item),el('td','',item.quantity||'Không nêu'),detail);body.append(tr)}table.append(body);vendorWork.append(table)}else vendorWork.append(el('p','report-note','Hồ sơ không nêu rõ.'));

 if(r.clarification_questions?.length){const questions=reportSection('Câu hỏi nháp');const list=el('ul','report-questions');for(const question of r.clarification_questions)list.append(el('li','',question));questions.append(list)}
 const submission=reportSection('Tài liệu cần nộp');
 const timeline=numberedSection(submission,1,'Các mốc');if(r.deadlines?.length){const grid=el('div','report-date-grid');for(const date of r.deadlines){const card=el('article','report-date'),head=el('div','report-date-head'),[statusText,statusClass]=date.conditional?['Theo điều kiện','unknown']:deadlineStatus(date.value),dateText=milestoneDateText(date.value);head.append(el('span','',date.label),el('span','report-date-status '+statusClass,statusText));card.append(head,el('strong','',dateText));if(date.note)card.append(el('p','',date.note));const source=sourceDetails(date.source_chunk_ids||[]);if(source)card.append(source);grid.append(card)}timeline.append(grid)}else timeline.append(el('p','report-note','Chưa xác định được mốc thời gian.'));
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
   head.append(el('span','report-status-tag '+(selected.length?'has-file':'missing-file'),selected.length?'Gợi ý':'Thiếu'));row.append(head);
   if(selected.length)row.append(el('div','report-file-summary','File gợi ý: '+selected.slice(0,2).map(file=>file.filename).join(' · ')+(selected.length>2?` · +${selected.length-2} file`:'')));
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
async function generateBidReport(){if(!latest.some(doc=>doc.chunks.length)||!llmReady)return;const runId=ensureRun('Tạo lại bản tổng hợp');const generation=++reportGeneration;reportRun.disabled=true;reportToolbar.hidden=true;reportStatus.className='meta';reportStatus.textContent='';showProcessingFiles(undefined,'Đang tạo bản tổng hợp');compareBox.hidden=true;try{const response=await fetch('/api/bid-report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({documents:latest,matches:latestMatch?.tag_matches||[]})});const data=await response.json();if(!response.ok)throw Error(data.error||'Không tạo được bản tổng hợp');if(generation!==reportGeneration)return;for(const usage of data.usage_events||[data.usage])addRunUsage(usage,runId);if(data.usage_missing&&activeRun?.id===runId)activeRun.unknownCost=true;for(const item of data.requirements||[]){const edit=reportOverrides.get(reportKey(item));if(edit)item.file_ids=edit.file_ids.filter(id=>library.some(file=>file.id===id))}latestReport=data;renderBidReport();hideProcessingFiles();compareBox.hidden=!(latestMatch?.tag_matches?.length);reportStatus.textContent='';if(activeRun?.id===runId)finishRun('Hoàn tất')}catch(error){if(generation!==reportGeneration)return;reportStatus.className='error';reportStatus.textContent='Lỗi tạo bản tổng hợp: '+error.message;hideProcessingFiles();compareBox.hidden=!(latestMatch?.tag_matches?.length);reportToolbar.hidden=!latestReport;if(activeRun?.id===runId){activeRun.unknownCost=true;finishRun('Lỗi tạo bản tổng hợp')}}finally{if(generation===reportGeneration)reportRun.disabled=false}}
reportRun.onclick=generateBidReport;reportPrint.onclick=()=>window.print();
window.addEventListener('beforeprint',()=>{const evaluation=document.querySelector('.report-evaluation');if(evaluation&&!evaluation.open){evaluation.open=true;evaluation.dataset.printOpened='true'}});
window.addEventListener('afterprint',()=>{const evaluation=document.querySelector('.report-evaluation[data-print-opened]');if(evaluation){evaluation.open=false;delete evaluation.dataset.printOpened}});
compareRetry.onclick=()=>{lastSuggestionKey='';scheduleSuggestions()};
loadLibrary();loadModelStatus();
exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify({schema_version:10,next_step_tags:nextStepTags(),documents:latest,file_suggestions:latestMatch,bid_report:latestReport,run_metrics:runHistory.map(run=>({label:run.label,duration_seconds:Number(metricDuration(run).split(' ')[0]),input_tokens:run.inputTokens,output_tokens:run.outputTokens,estimated_cost_usd:run.unknownCost?null:run.costUsd,api_calls:run.calls,note:run.note}))},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='suggested_files.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
