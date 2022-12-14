# Local Value Numbering
Local Value numberign


## Three steps:
  1. numbering: label all the numbers, O(N): one loop 
  2. reconstruct: reconstruct all the number: O(N) for one loop
  3. TDCE: trivil dead code elimination, O(N^2) for worst case

-NOTE: step 1 and step 2 are separated because of conflicting variable names:
  Rule: we must update the previous 

```
# Example
@main() {                   @main() {
    a: int = const 4;           lvn.0: int = const 4;
    print a;            =>      print lvn.0;
    a: int = const 3;           a: int = const 3;
    print a;                    print a;
}                           }
```


## To test the scriop
```
cd test
turnt *.bril
```
