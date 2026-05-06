#include <stdio.h>
#include "randArr.h"
#include "common.h"

#define ITER 2048
#define STRIDE 2
#define ARRAY_SIZE 5

__attribute__ ((noinline))
int loop(int zero)
{
	int data[5] = {1,2,3,4,5};
	int indices[ITER];
	int t = 0;
	int i;
	int a = 0;
	
	for(i = 0; i < ITER + zero; ++i)
	{
		indices[a] = (i * STRIDE) % ARRAY_SIZE;
		a += randArr[i];
	}

	for(i = 0; i < a + zero; ++i)
	{
		t += data[indices[i]];
	}

	return t;
}
int main(int argc, char* argv[])
{
	argc&=10000;
	ROI_BEGIN(); 
	int t=loop(argc); 
	ROI_END();
	volatile int a = t;
}
