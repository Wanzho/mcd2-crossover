.text
.globl __chkstk
__chkstk:
 pushq %rcx
 pushq %rax
 leaq 24(%rsp), %rcx
 cmpq $4096, %rax
 jb 2f
1:
 subq $4096, %rcx
 testb $0, (%rcx)
 subq $4096, %rax
 cmpq $4096, %rax
 jae 1b
2:
 subq %rax, %rcx
 testb $0, (%rcx)
 popq %rax
 popq %rcx
 retq
