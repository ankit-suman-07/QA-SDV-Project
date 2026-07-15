const byId = (id) => document.getElementById(id);
const valueOrUnavailable = (value) => value === null || value === undefined ? "Data unavailable" : value;
const formatTime = (value) => value ? new Date(value).toLocaleString() : "Data unavailable";

export function showLoading(){byId("messagePanel").hidden=false;byId("messagePanel").className="message-panel neutral";byId("messagePanel").textContent="Loading vehicle data...";byId("dashboardContent").hidden=true;}
export function showError(message="Vehicle monitoring service unavailable."){byId("messagePanel").hidden=false;byId("messagePanel").className="message-panel error";byId("messagePanel").textContent=message;byId("dashboardContent").hidden=true;byId("connectionStatus").textContent="ERROR";byId("connectionStatus").className="status-chip error";}
export function showDisconnected(){byId("messagePanel").hidden=false;byId("messagePanel").className="message-panel disconnected";byId("messagePanel").textContent="Vehicle disconnected — current telemetry is unavailable.";byId("dashboardContent").hidden=true;byId("connectionStatus").textContent="DISCONNECTED";byId("connectionStatus").className="status-chip disconnected";}

function healthPresentation(status, recovered){if(recovered)return{label:"RECOVERED",icon:"✓",message:"The previous fault condition has cleared.",className:"recovered"};return {HEALTHY:{label:"HEALTHY",icon:"✓",message:"No active vehicle faults detected.",className:"healthy"},WARNING:{label:"WARNING",icon:"⚠",message:"One or more vehicle conditions require attention.",className:"warning"},CRITICAL:{label:"CRITICAL",icon:"⛔",message:"A critical vehicle condition is active.",className:"critical"}}[status]||{label:"UNKNOWN",icon:"?",message:"Health status is unavailable.",className:"neutral"};}

export function renderVehicle(state,{recovered=false}={}){
  if(state.connectionStatus==="DISCONNECTED"){showDisconnected();return;}
  byId("messagePanel").hidden=true;byId("dashboardContent").hidden=false;
  byId("vehicleId").textContent=state.vehicleId||"Unknown vehicle";byId("connectionStatus").textContent="CONNECTED";byId("connectionStatus").className="status-chip healthy";
  const health=healthPresentation(state.healthStatus,recovered);byId("healthBanner").className=`health-banner ${health.className}`;byId("healthIcon").textContent=health.icon;byId("healthStatus").textContent=health.label;byId("healthMessage").textContent=health.message;
  byId("speedValue").textContent=valueOrUnavailable(state.speedKph);byId("batteryValue").textContent=valueOrUnavailable(state.batteryPercent);byId("temperatureValue").textContent=valueOrUnavailable(state.temperatureCelsius);byId("faultCount").textContent=valueOrUnavailable(state.faultCount);
  const tires=state.tirePressurePsi||{};byId("frontLeftValue").textContent=valueOrUnavailable(tires.frontLeft);byId("frontRightValue").textContent=valueOrUnavailable(tires.frontRight);byId("rearLeftValue").textContent=valueOrUnavailable(tires.rearLeft);byId("rearRightValue").textContent=valueOrUnavailable(tires.rearRight);
  byId("sourceTimestamp").textContent=formatTime(state.sourceTimestamp);byId("processedTimestamp").textContent=formatTime(state.processedTimestamp);byId("dataQuality").textContent=state.dataQuality||"CURRENT";
  renderFaults(state.activeFaults||[]);
}

export function renderFaults(faults){const list=byId("faultList");list.innerHTML="";byId("faultSummary").textContent=faults.length?`${faults.length} active fault${faults.length===1?"":"s"}`:"No active faults";if(!faults.length){list.innerHTML='<p class="empty-state">No active faults or diagnostic records.</p>';return;}faults.forEach(fault=>{const article=document.createElement("article");article.className="fault-card";article.innerHTML=`<header><h3>${fault.code}</h3><span class="status-chip ${fault.severity.toLowerCase()}">${fault.severity}</span></header><p>${fault.description}</p><dl><div><dt>Affected signal</dt><dd>${fault.affectedSignal}</dd></div><div><dt>Observed value</dt><dd>${fault.observedValue} ${fault.unit}</dd></div><div><dt>Threshold</dt><dd>${fault.threshold} ${fault.unit}</dd></div><div><dt>Status</dt><dd>${fault.status}</dd></div><div><dt>Detected</dt><dd>${formatTime(fault.detectedTimestamp)}</dd></div><div><dt>Correlation ID</dt><dd>${fault.correlationId}</dd></div></dl>`;list.appendChild(article);});}
