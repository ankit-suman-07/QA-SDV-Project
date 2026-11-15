import java.net.*;import java.net.http.*;import org.springframework.http.*;import org.springframework.http.client.*;import org.springframework.web.client.*;
class V1SpringProbe {public static void main(String[] a)throws Exception{
 var http=HttpClient.newBuilder().build();var factory=new JdkClientHttpRequestFactory(http);
 var client=RestClient.builder().requestFactory(factory).defaultHeaders(h->h.setBasicAuth(System.getenv("SDV_ACCEPTANCE_DITTO_USERNAME"),System.getenv("SDV_ACCEPTANCE_DITTO_PASSWORD"))).build();
 client.get().uri(URI.create(a[0]+"/api/2/things/sdv:vehicle-001")).accept(MediaType.APPLICATION_JSON).exchange((req,res)->{System.out.println(res.getStatusCode()+" "+new String(res.getBody().readAllBytes()));return 0;});
}}
