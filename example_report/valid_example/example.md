# ES2026 P1 Submission, Group AL-58

## Members
- Tomás Tempera, ist1110350, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1110350)
    + Issues assigned:[#1](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/1), [#3](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/3), [#7](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/7)
- Diogo Passinhas, ist1109554, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1109554)
    + Issues assigned: [#4](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/4),

## Total Coverage

+ [Total Test Coverage Screenshot](images/TotalCoverage.png)

## Tasks

### T1.1 - Implement Shift class with constructor, attributes, and unit tests

- Committer
  + Tomás Tempera, ist1110350, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1110350)
- Commit 
  + [#1](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/1)
- Review 
  + [MR #1](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/1)
- Coverage 
  + [Invariant Coverage Screenshot](images/shiftConstructor.png)


### T1.2 - Implement and test attribute length invariant in Shift class

- Committer
  + Diogo Passinhas, ist1109554, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1109554)
- Commit 
  + [#4](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/4)
- Review 
  + [MR #2](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/2)
- Coverage 
  + [Invariant Coverage Screenshot](images/shiftAttributeRequirements.png)


### T1.3 - Implement and test participants limit invariant in Shift class

- Committer
  + Tomás Tempera, ist1110350, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1110350)
- Commit 
  + [#7](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/7)
- Review 
  + [MR #3](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/3)
- Coverage 
  + [Invariant Coverage Screenshot](images/shiftParticipantsLimitPositive.png)


### T1.4 - Implement and test start date invariant in Shift class

- Committer
  + Tomás Tempera, ist1110350, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1110350)
- Commit 
  + [#3](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/3)
- Review 
  + [MR #4](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/4)
- Coverage 
  + [Invariant Coverage Screenshot](images/shiftStartTimeBeforeEndTime.png)


### T1.5 - Implement and test approved activity invariant in Shift class

- Committer
  + Diogo Passinhas, ist1109554, [GitLab link](https://gitlab.rnl.tecnico.ulisboa.pt/ist1109554)
- Commit 
  + [#8](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/issues/8)
- Review 
  + [MR #5](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/5) 
  + [MR #7](https://gitlab.rnl.tecnico.ulisboa.pt/es/es26-al-58/-/merge_requests/7)
- Coverage 
  + Before(MR #5): [Incomplete Coverage](images/shiftIncompleteActivityInvariant.png)
  + After(MR #7): [Complete Coverage](images/shiftActivityMustBeApproved.png)



---