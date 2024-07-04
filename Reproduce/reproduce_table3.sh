#/bin/bash
cd /plume/Plume/
mvn -Dtest=ReproduceTest#reproduceNewBugs test
cp /plume/Plume/table3.csv /plume/Reproduce/