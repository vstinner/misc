/*
 * Type and signness of common C types.
 *
 * Try to compile with -D_FILE_OFFSET_BITS=64 to get 64 bits off_t type.
 *
 * Types sorted by size:
 *
 * char < short < int <= long <= long long <= intmax_t
 *
 * long <= size_t = ssize_t <= void* = uintptr_t = intptr_t = ptrdiff_t <= intmax_t
 *
 * char < int <= wchar_t = wint_t <= intmax_t
 * long <= off_t <= intmax_t <= fpos_t
 * long <= time_t <= intmax_t
 *
 * float < double < long double
 */

/*

Articles:

http://www.unix.org/version2/whatsnew/lp64_wp.html
http://msdn.microsoft.com/en-us/library/ff564619.aspx
http://www.viva64.com/en/a/0050/
http://pubs.opengroup.org/onlinepubs/000095399/basedefs/stdint.h.html

Notes:

glib: GPOINTER_TO_INT, GINT_TO_POINTER

*/

/*

Targets, size in bytes:

------+-----+------+-------+---------
Name  | int | long | void* | Examples
------+-----+------+-------+---------
LP32  |   2 |    4 |     4 | MS-Dos
------+-----+------+-------+------------
ILP32 |   4 |    4 |     4 | UNIX 32-bit, Win32
------+-----+------+-------+------------
LLP64 |   4 |    4 |     8 | Win64
------+-----+------+-------+------------
LP64  |   4 |    8 |     8 | UNIX 64-bit
------+-----+------+-------+------------
ILP64 |   8 |    8 |     8 |
------+-----+------+-------+------------

char and short are always 1 and 2 bytes long.




Linux x86 (ILP32)
-----------------

_Bool:         8 bits, unsigned
char:          8 bits, signed
short:        16 bits, signed
int:          32 bits, signed
unsigned:     32 bits, unsigned
long:         32 bits, signed
long long:    64 bits, signed
intmax_t:     64 bits, signed
(__int128 not available)

void*:        32 bits, unsigned
funcptr_t:    32 bits, unsigned
size_t:       32 bits, unsigned
uintptr_t:    32 bits, unsigned
ssize_t:      32 bits, signed
intptr_t:     32 bits, signed
ptrdiff_t:    32 bits, signed

wchar_t:      32 bits, signed
wint_t:       32 bits, unsigned
time_t:       32 bits, signed
clock_t:      32 bits, signed

off_t:        32 bits, signed     (64 bits with -D_FILE_OFFSET_BITS=64)
fpos_t:       96 bits (struct)    (128 bits with -D_FILE_OFFSET_BITS=64)

uid_t:        32 bits, unsigned
gid_t:        32 bits, unsigned
pid_t:        32 bits, signed

float:        32 bits, signed
double:       64 bits, signed
long double:  96 bits, signed

Linux x86_64 (LP64)
-------------------

_Bool:         8 bits, unsigned
char:          8 bits, signed
short:        16 bits, signed
int:          32 bits, signed
unsigned:     32 bits, unsigned
long:         64 bits, signed
long long:    64 bits, signed
intmax_t:     64 bits, signed
__int128:     128 bits, signed

void*:        64 bits, unsigned
funcptr_t:    64 bits, unsigned
size_t:       64 bits, unsigned
uintptr_t:    64 bits, unsigned
ssize_t:      64 bits, signed
intptr_t:     64 bits, signed
ptrdiff_t:    64 bits, signed

wchar_t:      32 bits, signed
wint_t:       32 bits, unsigned
time_t:       64 bits, signed
clock_t:      64 bits, signed

off_t:        64 bits, signed
fpos_t:       128 bits (struct)

uid_t:        32 bits, unsigned
gid_t:        32 bits, unsigned
pid_t:        32 bits, signed

float:        32 bits, signed
double:       64 bits, signed
long double:  128 bits, signed

Linux x32
---------

XXX

Win32
-----

XXX

Win64
-----

XXX
*/

#include <stddef.h>   /* size_t (strlen), ptrdiff_t, wchar_t (wcslen)  */
#include <stdint.h>   /* intptr_t, uintptr_t */
#include <time.h>     /* time_t (time) */
#include <unistd.h>   /* ssize_t (read), off_t (lseek) */
#include <wchar.h>    /* wint_t (btowc) */

#include <stdio.h>    /* printf() */

#define TYPE_IS_SIGNED(TYPE)                     \
    ((TYPE)-1 < (TYPE)0)

#define TYPE_INFO(TYPE)                          \
    printf("%-13s %2u bits, %s\n",               \
           #TYPE ":",                            \
           sizeof(TYPE) * 8,                     \
           TYPE_IS_SIGNED(TYPE) ? "signed" : "unsigned")

#define STRUCT_INFO(TYPE)                          \
    printf("%-13s %2u bits (struct)\n",               \
           #TYPE ":",                            \
           sizeof(TYPE) * 8)

typedef void (*funcptr_t) (void);

int main()
{
    TYPE_INFO(_Bool);
    TYPE_INFO(char);
    TYPE_INFO(short);
    TYPE_INFO(int);
    TYPE_INFO(unsigned);
    TYPE_INFO(long);
    TYPE_INFO(long long);
    TYPE_INFO(intmax_t);
/* Custom types:
__int64: MSVC type for 64-bit integer (_I64_MIN, _I64_MAX, _UI64_MAX)
__int128: GCC type for 128-bit integer, need sizeof(long long) >= 16
*/
    printf("\n");

    TYPE_INFO(void*);
    TYPE_INFO(funcptr_t);
    TYPE_INFO(size_t);
    TYPE_INFO(uintptr_t);
    TYPE_INFO(ssize_t);
    TYPE_INFO(intptr_t);
    TYPE_INFO(ptrdiff_t);
    printf("\n");

    TYPE_INFO(wchar_t);
    TYPE_INFO(wint_t);
    TYPE_INFO(time_t);
    TYPE_INFO(clock_t);
    printf("\n");

    TYPE_INFO(off_t);
    STRUCT_INFO(fpos_t);
    printf("\n");

    TYPE_INFO(uid_t);
    TYPE_INFO(gid_t);
    TYPE_INFO(pid_t);
    printf("\n");

    TYPE_INFO(float);
    TYPE_INFO(double);
    TYPE_INFO(long double);
    return 0;
}
