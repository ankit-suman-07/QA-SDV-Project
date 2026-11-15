import java.net.*;import java.net.http.*;import java.util.*;
class V1DittoProbe {public static void main(String[] a)throws Exception{
 for(var v:HttpClient.Version.values()){
 var client=HttpClient.newBuilder().version(v).build();
 var req=HttpRequest.newBuilder(URI.create(a[0]+"/api/2/things/sdv:vehicle-001"))
 .header("Authorization","Basic "+Base64.getEncoder().encodeToString((System.getenv("SDV_ACCEPTANCE_DITTO_USERNAME")+":"+System.getenv("SDV_ACCEPTANCE_DITTO_PASSWORD")).getBytes())).header("Accept","application/json").GET().build();
 var res=client.send(req,HttpResponse.BodyHandlers.ofString());
 System.out.println(v+" "+res.statusCode()+" "+res.body());
 }}}
