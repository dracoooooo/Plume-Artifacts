package alg;

import graph.Edge;
import graph.Node;
import history.History;
import history.Operation;
import javafx.util.Pair;
import loader.ElleHistoryLoader;
import taps.TAP;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

public class PlumeList<VarType> extends Plume<VarType, ElleHistoryLoader.ElleValue> {
    public PlumeList(AlgType algType, History<VarType, ElleHistoryLoader.ElleValue> history, IsolationLevel isolationLevel, boolean enableGraphviz) {
        super(algType, history, isolationLevel, enableGraphviz);
        ZERO = new ElleHistoryLoader.ElleValue(null, new ArrayList<>());
    }

    @Override
    public void validate() {
        long startConstruction = System.nanoTime();
        buildCO();
        long endConstruction = System.nanoTime();
        long construction = (endConstruction - startConstruction) / 1_000_000;
        System.out.println("Construction: " + construction + "ms");

        long startTraversal = System.nanoTime();

        checkCOTAP();
        if (isolationLevel == IsolationLevel.RC) {
            return;
        }
        syncClock();
        buildWW();
        buildAO();
        if (!hasCircle(Edge.Type.AO)) {
            long endTraversal = System.nanoTime();
            long traversal = (endTraversal - startTraversal) / 1_000_000; // 转换为毫秒
            System.out.println("Traversal: " + traversal + "ms");
            return;
        }

        checkAOTAP();
        long endTraversal = System.nanoTime();
        long traversal = (endTraversal - startTraversal) / 1_000_000; // 转换为毫秒
        System.out.println("Traversal: " + traversal + "ms");
    }


    @Override
    protected void buildCO() {
        var hist = history.getFlatTransactions();
        Map<Long, Node<VarType, ElleHistoryLoader.ElleValue>> prevNodes = new HashMap<>();

        for (var txn: hist) {

            // update node with prev node
            var prev = prevNodes.get(txn.getSession().getId());
            var node = constructNode(txn, prev);
            graph.addVertex(node);
            prevNodes.put(txn.getSession().getId(), node);
            if (prev != null) {
                graph.addEdge(prev, node, new Edge<>(Edge.Type.SO, null));
            }

            var nearestRW = new HashMap<VarType, Operation<VarType, ElleHistoryLoader.ElleValue>>();
            var writesInTxn = new HashMap<VarType, Operation<VarType, ElleHistoryLoader.ElleValue>>();

            for (var op: txn.getOps()) {
                var key = new Pair<>(op.getVariable(), op.getValue());
                op2node.put(op, node);

                // if op is a read
                if (op.getType() == Operation.Type.READ) {

                    // check NonRepeatableRead and NotMyOwnWrite
                    var prevRW = nearestRW.get(op.getVariable());
                    if (prevRW != null && !op.getValue().equals(prevRW.getValue())) {
                        if (prevRW.getType() == Operation.Type.READ) {
                            findTAP(TAP.NonRepeatableRead);
                        } else {
                            boolean findNotMyLastWrite = false;
                            for (var prevOp: txn.getOps()) {
                                if (prevOp.getId() < prevRW.getId() &&
                                        prevOp.getType() == Operation.Type.WRITE &&
                                        prevOp.getVariable().equals(op.getVariable()) &&
                                        prevOp.getValue().equals(op.getValue())
                                ) {
                                    findNotMyLastWrite = true;
                                    findTAP(TAP.NotMyLastWrite);
                                }
                            }
                            if (!findNotMyLastWrite) {
                                findTAP(TAP.NotMyOwnWrite);
                            }
                        }
                    }
                    nearestRW.put(op.getVariable(), op);

                    var write = writes.get(key);
                    if (write != null) {
                        // if write -> op
                        // add op to reads
                        reads.computeIfAbsent(key, k -> new ArrayList<>()).add(op);

                        var writeNode = op2node.get(write);
                        if (!writeNode.equals(node)) {
                            if (!writeNode.canReachByCO(node)) {
                                node.updateCOReachability(writeNode);
                                graph.addEdge(writeNode, node, new Edge<>(Edge.Type.WR, op.getVariable()));
                            }
                            WREdges.computeIfAbsent(op.getVariable(), k -> new HashSet<>()).add(new Pair<>(writeNode, node));
                            WRNodesToOp.computeIfAbsent(new Pair<>(writeNode, node), wr -> new ArrayList<>()).add(new Pair<>(write, op));
                        }
                    } else if (op.getValue().equals(ZERO)) {
                        // if no write -> op, but op reads zero
                        reads.computeIfAbsent(key, k -> new ArrayList<>()).add(op);
                    } else {
                        readsWithoutWrites.computeIfAbsent(key, k -> new ArrayList<>()).add(op);
                    }
                } else {
                    // if op is a write
                    if (op.getValue().equals(ZERO)) {
                        // ignore write 0
                        continue;
                    }
                    writes.put(key, op);
                    writeNodes.computeIfAbsent(op.getVariable(), k -> new HashSet<>()).add(node);

                    nearestRW.put(op.getVariable(), op);

                    // check internal write
                    var internalWrite = writesInTxn.get(op.getVariable());
                    if (internalWrite != null) {
                        internalWrites.add(internalWrite);
                    }
                    writesInTxn.put(op.getVariable(), op);

                    var pendingReads = readsWithoutWrites.get(key);
                    if (pendingReads != null) {
                        reads.computeIfAbsent(key, k -> new ArrayList<>()).addAll(pendingReads);
                        for (var pendingRead: pendingReads) {
                            var pendingReadNode = op2node.get(pendingRead);
                            if (!node.equals(pendingReadNode)) {
                                graph.addEdge(node, pendingReadNode, new Edge<>(Edge.Type.WR, op.getVariable()));
                                WREdges.computeIfAbsent(op.getVariable(), k -> new HashSet<>()).add(new Pair<>(node, pendingReadNode));
                                WRNodesToOp.computeIfAbsent(new Pair<>(node, pendingReadNode), wr -> new ArrayList<>()).add(new Pair<>(op, pendingRead));
                            }
                        }
                    }
                    readsWithoutWrites.remove(key);
                }
            }
            updateVec(new HashSet<>(), node, node, Edge.Type.CO);
        }
    }

    private void buildWW() {
        Set<Node<VarType, ElleHistoryLoader.ElleValue>> pendingNodes = new HashSet<>();
        reads.values().forEach((readList) -> {
            readList.forEach((read) -> {
                var ref = new Object() {
                    Node<VarType, ElleHistoryLoader.ElleValue> prev = null;
                };
                read.getValue().getList().forEach((val) -> {
                    var key = new Pair<>(read.getVariable(), new ElleHistoryLoader.ElleValue(val, null));
                    var write = writes.get(key);
                    if (write == null) {
                        return;
                    }
                    var node = op2node.get(write);
                    if (ref.prev == null) {
                        ref.prev = node;
                        pendingNodes.add(ref.prev);
                    }
                    graph.addEdge(ref.prev, node, new Edge<>(Edge.Type.AO, null));
                    ref.prev = node;
                });
            });
        });
        pendingNodes.forEach((node) -> {
            updateVec(new HashSet<>(), node, node, Edge.Type.AO);
        });
    }

    @Override
    protected void checkCOTAP() {
        // check aborted read and thin air
        if (readsWithoutWrites.size() > 0) {
            AtomicInteger count = new AtomicInteger();
            readsWithoutWrites.keySet().forEach((key) -> {
                if (history.getAbortedWrites().contains(key)) {
                    // find aborted read
                    findTAP(TAP.AbortedRead);
                    count.addAndGet(1);
                }
            });
            if (count.get() != readsWithoutWrites.size()) {
                // find thin air read
                findTAP(TAP.ThinAirRead);
            }
        }

        // for each read
        reads.values().forEach((readList) -> {
            readList.forEach((read) -> {
                read.getValue().getList().forEach((v) -> {
                    var key = new Pair<>(read.getVariable(),  new ElleHistoryLoader.ElleValue(v, null));
                    var node = op2node.get(read);

                    // read(x, 0)
                    if (read.getValue().equals(ZERO)) {
                        var writeRelNodes = writeNodes.get(read.getVariable());

                        // no write(x, k)
                        if (writeRelNodes == null) {
                            return;
                        }

                        // check if write(x, k) co-> read
                        writeRelNodes.forEach((writeNode) -> {
                            if (writeNode.equals(node)) {
                                return;
                            }
                            if (writeNode.canReachByCO(node)) {
                                // there are 3 cases: initReadMono initReadWR or writeCOInitRead
                                boolean findSubTap = false;
                                for (var writeY : writeNode.getTransaction().getOps()) {
                                    for (var readY : node.getTransaction().getOps()) {
                                        if (!writeY.getVariable().equals(read.getVariable()) &&
                                                writeY.getType().equals(Operation.Type.WRITE) &&
                                                readY.getType().equals(Operation.Type.READ) &&
                                                writeY.getVariable().equals(readY.getVariable()) &&
                                                writeY.getValue().equals(readY.getValue())) {
                                            // find w(y, v_y) wr-> r(y, v_y)
                                            findSubTap = true;
                                            if (readY.getId() < read.getId()) {
                                                // find initReadMono if read y precedes read x
                                                findTAP(TAP.NonMonoReadCO);
                                            } else {
                                                // find initReadWR
                                                findTAP(TAP.FracturedReadCO);
                                            }
                                        }
                                    }
                                }
                                if (!findSubTap) {
                                    // find initReadCO if not InitReadMono or InitReadWR
                                    findTAP(TAP.COConflictAO);
                                }
                            }
                        });
                        return;
                    }

                    // write wr-> read
                    var write = writes.get(key);
                    var writeNode = op2node.get(write);

                    if (writeNode == null) {
                        return;
                    }

                    if (!writeNode.equals(node)) {
                        // in different txn, and v should be the last element in the read list
                        if (internalWrites.contains(write) && read.getValue().getLastElement().equals(v)) {
                            // find intermediate write
                            findTAP(TAP.IntermediateRead);
                        }
                    } else {
                        // in same txn
                        if (write.getId() > read.getId()) {
                            // find future read
                            findTAP(TAP.FutureRead);
                        }
                    }
                });
            });
        });

        // check CyclicCO
        // iter wr edge (t1 wr-> t2)
        WREdges.forEach((varX, edgesX) -> {
            edgesX.forEach((edge) -> {
                var t1 = edge.getKey();
                var t2 = edge.getValue();
                if (t1.canReachByCO(t2) && t2.canReachByCO(t1)) {
                    // find cyclicCO
                    findTAP(TAP.CyclicCO);
                    print2TxnBp(t1, t2);
                }
            });
        });
    }
}
