// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from "vitest";
import { renderVehicle, showDisconnected, showError, showLoading } from "../js/ui.js";

const ids=["messagePanel","dashboardContent","connectionStatus","vehicleId","healthBanner","healthIcon","healthStatus","healthMessage","speedValue","batteryValue","temperatureValue","faultCount","frontLeftValue","frontRightValue","rearLeftValue","rearRightValue","sourceTimestamp","processedTimestamp","dataQuality","faultSummary","faultList"];
beforeEach(()=>{document.body.innerHTML=ids.map(id=>`<div id="${id}"></div>`).join("");});
const base={vehicleId:"vehicle-001",connectionStatus:"CONNECTED",sourceTimestamp:"2026-07-15T14:30:00Z",speedKph:60,batteryPercent:75,temperatureCelsius:85,tirePressurePsi:{frontLeft:32,frontRight:32,rearLeft:31,rearRight:32},healthStatus:"HEALTHY",activeFaults:[],faultCount:0,processedTimestamp:"2026-07-15T14:30:00.120Z"};

describe("dashboard UI states",()=>{
  it("displays loading state",()=>{showLoading();expect(document.getElementById("messagePanel").textContent).toContain("Loading vehicle data");});
  it("displays healthy state",()=>{renderVehicle(base);expect(document.getElementById("healthStatus").textContent).toBe("HEALTHY");});
  it("displays warning state",()=>{renderVehicle({...base,healthStatus:"WARNING"});expect(document.getElementById("healthStatus").textContent).toBe("WARNING");});
  it("displays critical state",()=>{renderVehicle({...base,healthStatus:"CRITICAL"});expect(document.getElementById("healthStatus").textContent).toBe("CRITICAL");});
  it("displays recovered state",()=>{renderVehicle(base,{recovered:true});expect(document.getElementById("healthStatus").textContent).toBe("RECOVERED");});
  it("displays disconnected state",()=>{showDisconnected();expect(document.getElementById("messagePanel").textContent).toContain("disconnected");});
  it("displays API error state",()=>{showError();expect(document.getElementById("messagePanel").textContent).toContain("unavailable");});
  it("renders active fault diagnostic details",()=>{renderVehicle({...base,healthStatus:"CRITICAL",faultCount:1,activeFaults:[{code:"TEMPERATURE_HIGH",description:"High temperature",severity:"CRITICAL",status:"ACTIVE",affectedSignal:"temperatureCelsius",observedValue:110,unit:"°C",threshold:105,detectedTimestamp:"2026-07-15T14:30:00Z",correlationId:"corr-1"}]});expect(document.getElementById("faultList").textContent).toContain("TEMPERATURE_HIGH");expect(document.getElementById("faultList").textContent).toContain("110");});
  it("does not convert missing signal values to zero",()=>{renderVehicle({...base,speedKph:null});expect(document.getElementById("speedValue").textContent).toBe("Data unavailable");});
});
