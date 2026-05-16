// Redding Downtown map variables and Redding-specific macros
// Ported from RP source REDDOWN.H and PARTY.H (not in data/headers/)
#ifndef RCDRJOHN_H
#define RCDRJOHN_H

// Skill ID missing from data/headers/define.h
#define SKILL_CONVERSANT            (14)

// Map variables (Redding Downtown map)
#define MVAR_Fannie_Mae             (0)
#define MVAR_Widow_Rooney           (1)
#define MVAR_Made_Car               (2)
#define MVAR_Attecked_Cashier       (3)
#define MVAR_Using_Locked_Door      (4)
#define MVAR_Rehab_Time             (5)

// Fannie Mae states
#define FANNIE_NONE                 (0)
#define FANNIE_CUSTOMER             (1)
#define FANNIE_MONEY_ASKED          (2)
#define FANNIE_MONEY_GIVEN          (3)
#define FANNIE_SICK                 (4)
#define FANNIE_SICKER               (5)
#define FANNIE_DEAD                 (6)
#define FANNIE_CURED_DUDE           (7)
#define FANNIE_CURED_DOC            (8)
#define FANNIE_CURED_LOU            (9)

#define set_fannie(x)               set_map_var(MVAR_Fannie_Mae,x)
#define fannie                      map_var(MVAR_Fannie_Mae)
#define fannie_cured                ((fannie == FANNIE_CURED_DUDE) or (fannie == FANNIE_CURED_DOC) or (fannie == FANNIE_CURED_LOU))

// Party health tracking (from RP PARTY.H — absent from data/headers/party.h)
variable How_Many_Party_Members_Are_Injured;
variable How_Many_Party_Members_Armed;

#define If_Party_Has_Injured                                                    \
   How_Many_Party_Members_Are_Injured := 0;                                     \
   if (Vic_In_Party) then                                                       \
      if (Is_Injured(Vic_Ptr)) then                                             \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Myron_In_Party) then                                                     \
      if (Is_Injured(Myron_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Marcus_In_Party) then                                                    \
      if (Is_Injured(Marcus_Ptr)) then                                          \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (MacRae_In_Party) then                                                    \
      if (Is_Injured(MacRae_Ptr)) then                                          \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Sulik_In_Party) then                                                     \
      if (Is_Injured(Sulik_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Lenny_In_Party) then                                                     \
      if (Is_Injured(Lenny_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Cyberdog_In_Party) then                                                  \
      if (Is_Injured(Cyberdog_Ptr)) then                                        \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Doc_In_Party) then                                                       \
      if (Is_Injured(Doc_Ptr)) then                                             \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Goris_In_Party) then                                                     \
      if (Is_Injured(Goris_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Davin_In_Party) then                                                     \
      if (Is_Injured(Davin_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Miria_In_Party) then                                                     \
      if (Is_Injured(Miria_Ptr)) then                                           \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Dogmeat_In_Party) then                                                   \
      if (Is_Injured(Dogmeat_Ptr)) then                                         \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (K9_In_Party) then                                                        \
      if (Is_Injured(K9_Ptr)) then                                              \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Kitsune_In_Party) then                                                   \
      if (Is_Injured(Kitsune_Ptr)) then                                         \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Dex_In_Party) then                                                       \
      if (Is_Injured(Dex_Ptr)) then                                             \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (Cat_Jules_In_Party) then                                                 \
      if (Is_Injured(Cat_Jules_Ptr)) then                                       \
         How_Many_Party_Members_Are_Injured+=1;                                 \
   if (How_Many_Party_Members_Are_Injured > 0)

#endif // RCDRJOHN_H
