# snippet below is used in DM Total report in Excel
=IF(D2<>0, "Pending", IF(AND(SUM(F2,E2)=J2, OR(K2="dmready", K2="dmproc")), "Y", "N"))

# snippet below is used in DM Total report in Excel to denote whether feature is part of SW inventory.
=IF(OR(Q2="ALLEGHENY", Q2="ARMSTRONG", Q2="BEAVER", Q2="BUTLER", Q2="FAYETTE", Q2="GREENE", Q2="INDIANA", Q2="LAWRENCE", Q2="WASHINGTON", Q2="WESTMORELAND"), "Y", "N")



=IF(C2<>0, "Y", IF(AND(SUM(E2,D2)=I2, OR(K2="dmready", K2="dmproc")), "N", "Y"))