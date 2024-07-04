import alg.AlgType;
import alg.IsolationLevel;
import alg.Plume;
import alg.PlumeList;
import loader.ElleHistoryLoader;
import loader.TextHistoryLoader;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.function.Function;

public class ReproduceTest {
    private final String reproduceAllPath = "/plume/History/reproduce/";

    private final String newBugsPath = "/plume/History/bugs/";

    private final String ednTestcasePath = "/plume/History/testcase/elle/";

    private final String txtTestcasePath = "/plume/History/testcase/text/";


    private static int count = 0;

    private static final Map<String, Integer> sumMap = new HashMap<>();


    public static void writeMapToCSV(String keyCol, String valCol, Map<String, Integer> map, String filePath) {
        Map<String, Integer> sortedMap = new TreeMap<>(map);
        try (FileWriter writer = new FileWriter(filePath)) {
            writer.append(keyCol);
            writer.append(",");
            writer.append(valCol
            );
            writer.append("\n");

            for (Map.Entry<String, Integer> entry : sortedMap.entrySet()) {
                writer.append(entry.getKey());
                writer.append(",");
                writer.append(String.valueOf(entry.getValue()));
                writer.append("\n");
            }
        } catch (IOException e) {
        }
    }

    private void runFile(File file) {
        if (file.getName().endsWith(".txt")) {
            System.out.println(file.getAbsolutePath());
            var historyLoader = new TextHistoryLoader(file);
            var history = historyLoader.loadHistory();
            var plume = new Plume<>(AlgType.PLUME, history, IsolationLevel.TCC, false);
            plume.validate();
            if(!plume.getBadPatternCount().isEmpty()) {
                plume.getBadPatternCount().forEach((k, v) -> sumMap.merge(k, 1, Integer::sum));
                count += 1;
            }
        }
        if (file.getName().endsWith(".edn")) {
            System.out.println(file.getAbsolutePath());
            var historyLoader = new ElleHistoryLoader(file);
            var history = historyLoader.loadHistory();
            var plume = new PlumeList<>(AlgType.PLUME_LIST, history, IsolationLevel.TCC, false);
            plume.validate();
            if(!plume.getBadPatternCount().isEmpty()) {
                plume.getBadPatternCount().forEach((k, v) -> sumMap.merge(k, 1, Integer::sum));
                count += 1;
            }
        }
    }

    private void traverseFolder(String folderPath) {
        File folder = new File(folderPath);
        if (folder.exists()) {
            File[] files = folder.listFiles();
            if (files != null) {
                for (File file : files) {
                    if (file.isDirectory()) {
                        traverseFolder(file.getAbsolutePath());
                    } else {
                        runFile(file);
                    }
                }
            }
        }
    }

    @Test
    void reproduceAllBugs() {
        traverseFolder(reproduceAllPath);
        List<String> keys = new ArrayList<>(sumMap.keySet());
        Collections.sort(keys);
        for (String key : keys) {
            int val = sumMap.get(key);
            System.out.print(key + ":" + val + ";");
        }
        int sum = sumMap.values().stream().mapToInt(Integer::intValue).sum();
        sumMap.put("#TAPs", sum);
        sumMap.put("#Hist", count);

        writeMapToCSV("TAP", "Count", sumMap, "./table4.csv");
    }

    @Test
    void reproduceNewBugs() {
        Function<String, Integer> runNewBug = (String path) -> {
            long startTime = System.currentTimeMillis();
            runFile(new File(path));
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            return Math.toIntExact(duration);
        };
        Path dir = Paths.get(newBugsPath);
        Map<String, Integer> result = new HashMap<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir)) {
            for (Path entry : stream) {
                if (Files.isRegularFile(entry)) {
                    String path = entry.toAbsolutePath().toString();
                    result.put(path, runNewBug.apply(path));
                }
            }
        } catch (IOException ignored) {
        }
        System.out.println(result);
        writeMapToCSV("Bug Path", "Time(ms)", result, "./table3.csv");
    }

    @Test
    void ednTestcase() {
        traverseFolder(ednTestcasePath);
        System.out.println(count);
        System.out.println(sumMap);
    }

    @Test
    void txtTestcase() {
        traverseFolder(txtTestcasePath);
        System.out.println(count);
        System.out.println(sumMap);
    }
}
