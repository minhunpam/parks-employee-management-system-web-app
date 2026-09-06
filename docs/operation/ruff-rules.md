# Rules excluded for linting
I001 unsorted imports
SIM117 multiple `with` statements --- Currently I don't use it in the main codebase, only in tests and I only use doubly nested `with` statements, so the readability is not too bad

# Ruff selected for formatting
`F401` unused import
`F841` unused variable
`E713` not in test --- instead of `not ... in`
`E703` statement ends with an unnecessary semicolon --- sometimes muscle memory of C and C++ just kicked in out of nowhere
`SIM108` if-else blocks can be replaced with ternary operator