#!/usr/bin/env sh
set -eu

fuseki_gsp_url="${TSKG_FUSEKI_GSP_URL:-http://localhost:3030/traffic-signs/data}"
ontology_graph="https%3A%2F%2Fexample.org%2Ftraffic-sign-kg%2Fgraph%2Fontology"
shapes_graph="https%3A%2F%2Fexample.org%2Ftraffic-sign-kg%2Fgraph%2Fshapes"

curl --fail --silent --show-error \
  -X PUT \
  -H "Content-Type: text/turtle" \
  --data-binary @ontology/traffic-sign-ontology.ttl \
  "${fuseki_gsp_url}?graph=${ontology_graph}"

curl --fail --silent --show-error \
  -X PUT \
  -H "Content-Type: text/turtle" \
  --data-binary @ontology/traffic-sign-shapes.ttl \
  "${fuseki_gsp_url}?graph=${shapes_graph}"

echo "Loaded ontology and SHACL shapes into Fuseki."

