
package com.ankit.sdv.backend.config;

import com.ankit.sdv.backend.service.VehicleEventConsumer;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.mqtt.inbound.MqttPahoMessageDrivenChannelAdapter;
import org.springframework.integration.mqtt.support.DefaultPahoMessageConverter;
import org.springframework.integration.mqtt.core.DefaultMqttPahoClientFactory;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.GenericMessage;

@Configuration
@ConditionalOnProperty(
        name = "sdv.mqtt.enabled",
        havingValue = "true"
)
public class MqttConfig {

    @Bean
    public MessageChannel mqttInputChannel(
            VehicleEventConsumer consumer
    ) {
        DirectChannel channel = new DirectChannel();

        channel.subscribe(message ->
                consumer.receive(
                        new GenericMessage<>(
                                message.getPayload().toString(),
                                message.getHeaders()
                        )
                )
        );

        return channel;
    }

    @Bean
    public DefaultMqttPahoClientFactory mqttClientFactory(
            @Value("${sdv.mqtt.broker-url}") String brokerUrl
    ) {
        MqttConnectOptions options = new MqttConnectOptions();
        options.setServerURIs(new String[]{brokerUrl});
        options.setAutomaticReconnect(true);
        options.setCleanSession(true);

        DefaultMqttPahoClientFactory factory =
                new DefaultMqttPahoClientFactory();
        factory.setConnectionOptions(options);

        return factory;
    }

    @Bean
    public MqttPahoMessageDrivenChannelAdapter mqttInboundAdapter(
            DefaultMqttPahoClientFactory factory,
            @Qualifier("mqttInputChannel") MessageChannel mqttInputChannel,
            @Value("${sdv.mqtt.client-id}") String clientId,
            @Value("${sdv.mqtt.topic}") String topic
    ) {
        MqttPahoMessageDrivenChannelAdapter adapter =
                new MqttPahoMessageDrivenChannelAdapter(
                        clientId,
                        factory,
                        topic
                );

        adapter.setCompletionTimeout(5000);
        adapter.setConverter(new DefaultPahoMessageConverter());
        adapter.setQos(1);
        adapter.setOutputChannel(mqttInputChannel);

        return adapter;
    }
}
