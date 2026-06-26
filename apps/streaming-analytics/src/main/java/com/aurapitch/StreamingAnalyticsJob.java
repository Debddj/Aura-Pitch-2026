package com.aurapitch;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingProcessingTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;

public class StreamingAnalyticsJob {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        KafkaSource<TacticalEvent> source = KafkaSource.<TacticalEvent>builder()
            .setBootstrapServers("kafka:9092")
            .setTopics("tactical-stream")
            .setGroupId("aurapitch-consumer")
            .setStartingOffsets(OffsetsInitializer.latest())
            .setValueOnlyDeserializer(new TacticalEventDeserializationSchema())
            .build();

        DataStream<TacticalEvent> stream = env
            .fromSource(source, WatermarkStrategy.forMonotonousTimestamps(), "Kafka Source");

        stream
            .keyBy(event -> event.getPlayerId())
            .window(TumblingProcessingTimeWindows.of(Time.seconds(5)))
            .aggregate(new PlayerActivityAggregator())
            .addSink(new FlinkGrafanaSink());

        env.execute("Aura-Pitch Real-Time Analytics");
    }
}
