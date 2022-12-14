# Local Value Numbering
Local Value numbering for dead code elimination.
This implememtation perfer certain style which is not usable for real world 
application.

## To test the script
```
cd test
turnt *.bril
```
We can see `logical-operators.bril` and `clobber-fold.bril` failed to pass 
the check but follow the concept of local value numbering.

## Big picture: Three steps:
  1. numbering: label all the numbers, O(N): one loop 
  2. reconstruct: reconstruct all the number: O(N) for one loop
  3. TDCE: trivil dead code elimination, O(N^2) for worst case

```
# Example                   # correct! 
@main() {                   @main() {
    a: int = const 4;           lvn.0: int = const 4;
    print a;            =>      print lvn.0;
    a: int = const 3;           a: int = const 3;
    print a;                    print a;
}                           }
```

## Observation: data strucutre a 3-tuple table
can be implemented by 3 hashmap to the tuple for querying or 3! hashmap (factorial) for querying

## Observation: extension are done in reconstruction stage.
the extensions can all benefit from numbering.

## Discussions: can we combine the numbering and the reconstruction step?
It seems doable if we updated the latter conflicting variable name (a.k.a later canonical home). This will introduce another hashmap for remembering the latest variable name's alias. This won't be local value numbering but just a varaible-to-value map. (a.k.a home-to-value map)
Will we be able to do the propagation/const-folding as well?

## Things I don't like for this specific implementation
1. This implementation treat 'original id operation' and 'derived id operation' 
differently, which is odd.



