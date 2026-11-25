# Distributed (multi-node) protocol: NOT EXECUTED

Status: **not executed**. All results of this project come from one machine with `local[p]`, where p is the number of
cores granted to one Spark JVM. This is local parallelism, not a cluster: no network transfer, a single disk, shared
memory bandwidth. Conclusions about multi-node behaviour are therefore not claimed.

Protocol that would be executed on a homogeneous cluster (same tooling as the local runs):

1. Same code, `--master spark://...` or YARN/Kubernetes, p in {1, 2, 4} identical nodes, fixed cores and memory per node,
   dynamic allocation off, same AQE policy for B2, B3 and B4.
2. Data on storage reachable by all nodes (distributed file system or object store); the same prepared Parquet and FLAC
   manifests; report whether reads are local or remote.
3. Same grid (p x P x lot) and repetition counts; event logs on a shared directory for the History Server;
   per-node CPU, memory, network and disk metrics collected on all nodes (not only the driver).
4. Same selector: calibrate on the calibration lots, freeze the margin, evaluate on the held-out lots.
5. Additional measurements that local mode cannot give: remote shuffle bytes, network throughput, node-failure behaviour.
