FROM eclipse-temurin:21-jre-alpine

ARG JENA_VERSION=6.1.0
ARG MAVEN_REPOSITORY=https://repo1.maven.org/maven2
ARG JAR_PATH=org/apache/jena/jena-fuseki-server/${JENA_VERSION}/jena-fuseki-server-${JENA_VERSION}.jar

RUN apk add --no-cache curl \
    && mkdir -p /fuseki/databases \
    && curl --fail --location --retry 3 \
       "${MAVEN_REPOSITORY}/${JAR_PATH}" \
       --output /fuseki/fuseki.jar \
    && expected="$(curl --fail --silent --show-error \
       "${MAVEN_REPOSITORY}/${JAR_PATH}.sha1")" \
    && echo "${expected}  /fuseki/fuseki.jar" | sha1sum -c - \
    && addgroup -g 1000 fuseki \
    && adduser -D -H -u 1000 -G fuseki fuseki \
    && chown -R fuseki:fuseki /fuseki

WORKDIR /fuseki
USER fuseki
EXPOSE 3030

ENTRYPOINT ["java", "-cp", "/fuseki/fuseki.jar", "org.apache.jena.fuseki.main.cmds.FusekiMainCmd"]
