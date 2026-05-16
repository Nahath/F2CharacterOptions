// San Francisco (Shi) map macros for Dr. Fung
// Ported from RP source SANFRAN.H (not present in data/headers/)
#ifndef FCDRFUNG_H
#define FCDRFUNG_H

// Shi enemy / global san-fran flags (GVAR_SAN_FRAN_FLAGS bit fields)
#define SF_SHI_ENEMY               bit_1
#define SF_ELRON_ENEMY             bit_19

#define san_fran_flag(x)           gvar_bit(GVAR_SAN_FRAN_FLAGS, x)
#define set_san_fran_flag(x)       set_gvar_bit_on(GVAR_SAN_FRAN_FLAGS, x)

// Elronologist quest state (GVAR_SAN_FRAN_ELRON)
#define EL_ACCEPTED                bit_4

#define elron_flag_any             (global_var(GVAR_SAN_FRAN_ELRON))

// Spleen quest states (GVAR_SAN_FRAN_SPLEEN)
#define SP_ACCEPTED                1
#define SP_TALKWONG                2
#define SP_FOUND                   3
#define SP_UNPAID                  4
#define SP_FUNGCHARGE              5
#define SP_FUNGFREE                6

#define spleen_flag(x)             (global_var(GVAR_SAN_FRAN_SPLEEN) == x)
#define set_spleen_flag(x)         set_global_var(GVAR_SAN_FRAN_SPLEEN, x)

// Doc Holiday known flag
#define KNOW_DOC_HOLIDAY           global_var(GVAR_KNOW_DOC_HOLIDAY)

// NavCom parts PID (same item as PID_NAV_COMPUTER_PARTS)
#define PID_NAVCOM_PARTS           (479)

#endif // FCDRFUNG_H
