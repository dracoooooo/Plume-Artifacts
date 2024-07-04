package util;

public class DFSCounter {
    private static int count = 0;

    public static void increment() {
        count++;
    }

    public static int getCount() {
        return count;
    }
}