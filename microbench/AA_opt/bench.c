#include <stdio.h>
#include <stdlib.h>     /* malloc, free, rand */

#include "../common.h"

#define ASIZE 2048
#define STEP   128
#define ITERS    2
#define LEN  32768

int num_alloc = 0;
struct ll* curr_alloc;
int arr[ASIZE];

//make sure struct occupies an entire cache line.
struct ll {
  int val;
  struct ll* _next;
};

__attribute__ ((noinline))
int loop(int zero,struct ll* n) {
  int t = 0,i,iter;
  for(iter=0; iter < ITERS; ++iter) {
    struct ll* cur =n;
    while(cur!=NULL) {
      t+=cur->val;
      cur=cur->_next;
    }
  }
  return t;
}

struct ll* alloc_ll_node() {
  if (!num_alloc)
  {
    curr_alloc = malloc(5 * sizeof(struct ll));
  }

  struct ll* r = curr_alloc + (num_alloc);
  if (++num_alloc == 5)
  {
    num_alloc = 0;
  }

  return r;
}

int main(int argc, char* argv[]) {
   argc&=10000;
   struct ll *n, *cur;

   int i;
   n=alloc_ll_node();
   cur=n;
   for(i=0;i<LEN;++i) {
     cur->val=i;
     cur->_next=alloc_ll_node();
     malloc(3*64); // trash the cache
     cur=cur->_next;
   }
   cur->val=100;
   cur->_next=NULL;

   ROI_BEGIN(); 
   int t=loop(argc,n);
   ROI_END();

   volatile int a = t;
}

