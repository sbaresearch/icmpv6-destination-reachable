#include <stdio.h>

//#define INITIAL_JIFFIES 

int main() {
    // Define the HZ values for 250 and 1000 HZ
    unsigned int HZ_250 = 250;
    unsigned int HZ_1000 = 1000;

    // Calculate INITIAL_JIFFIES for 250 HZ and 1000 HZ
    unsigned long initial_jiffies_250 = ((unsigned long)(unsigned int)(-300 * HZ_250));
    unsigned long initial_jiffies_1000 = (unsigned long)(unsigned int)(-300 * HZ_1000);

    // Print the results
    printf("INITIAL_JIFFIES for 250 HZ: %lu\n", initial_jiffies_250);
    printf("INITIAL_JIFFIES for 1000 HZ: %lu\n", initial_jiffies_1000);

    return 0;
}
