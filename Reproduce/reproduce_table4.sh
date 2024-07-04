#/bin/bash
cd /plume/Plume/
mvn -Dtest=ReproduceTest#reproduceAllBugs test
cp /plume/Plume/table4.csv /plume/Reproduce/