// Vault City courtyard map variables (from VCtyCtyd.h)
#ifndef VCTYCTYD_VCANDY_H
#define VCTYCTYD_VCANDY_H

#define MVAR_Remove_Skeeve      (0)
#define MVAR_Made_Car           (1)
#define MVAR_Stealing_From_Harry (2)
#define MVAR_Guard_Alert        (3)
#define MVAR_Auto_Doc_Fixed     (4)
#define MVAR_Wrench             (5)
#define MVAR_Made_Payoff        (6)
#define MVAR_Saw_Raiders        (7)

// If_Party_Has_Injured — counts injured party members, leaves condition for "then begin"
// (ported from RP source PARTY.H since data/headers/party.h omits this macro)
variable How_Many_Party_Members_Are_Injured;

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

#endif // VCTYCTYD_VCANDY_H
