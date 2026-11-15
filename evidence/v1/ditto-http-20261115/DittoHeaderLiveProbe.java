package com.ankit.sdv.backend.config;
import java.net.*;
import java.net.http.*;
import java.time.*;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import com.ankit.sdv.backend.service.*;

public class DittoHeaderLiveProbe {
 public static void main(String[] args) throws Exception {
  String user=System.getenv("SDV_DITTO_USERNAME"), pass=System.getenv("SDV_DITTO_PASSWORD");
  var timeout=Duration.ofSeconds(3); var base=URI.create(args[0]);
  var factory=new JdkClientHttpRequestFactory(HttpClient.newHttpClient());factory.setReadTimeout(timeout);
  var baseline=RestClient.builder().requestFactory(factory).defaultHeaders(h->h.setBasicAuth(user,pass)).build();
  int oldStatus=baseline.get().uri(base+"/api/2/things/sdv:vehicle-001").exchange((q,r)->r.getStatusCode().value());
  System.out.println("BASELINE_STATUS="+oldStatus);
  if(oldStatus!=400)throw new AssertionError("Expected real baseline duplicate-header failure");
  var p=new V1DittoProperties("live",base,timeout,timeout,Duration.ofSeconds(5),Duration.ofSeconds(30),user,pass,null);
  var reader=new V1DittoConfiguration().httpVehicleTwinReader(p);
  for(String id:p.vehicleIds()) {
   var snapshot=reader.read(id,p.things().get(id)).orElseThrow();
   System.out.println("READ_OK="+id+" event="+snapshot.lastEventId()+" source="+snapshot.sourceTimestamp());
  }
  var clock=Clock.systemUTC();
  try(var fleet=new FleetService(new V1VehicleService(reader,p,clock),p,clock);
      var writer=new FleetConfiguration().fleetMaterializer(fleet,new FleetProperties(true,timeout,timeout,timeout,user,pass),p,clock)) {
   writer.update();
   if(writer.lastSuccess()==null||writer.failureCount()!=0)throw new AssertionError("Fleet write failed");
   System.out.println("FLEET_WRITE_OK=true");
  }
 }
}
