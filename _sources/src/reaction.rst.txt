Emoji Reaction
==========================

The following diagrams shows workflow in case a reaction is added by user.

Main reaction schedule
----------------------

.. mermaid ::
    graph TD
    A[Start] --> B([Emoji added])
    B --> C[[Add reaction to DB]]
    C --> D[[Get all valid games]]
    D --> E{valid game<br>for reation?}
    E --> |no| B
    E --> |yes| F[[Get all valid player]]
    F --> G[[Game Reaction Schedule]]
    G --> H[[Update reaction in DB]]
    H --> B

Game Reaction Schedule
----------------------

.. mermaid ::
    graph TD
    AA[Start] --> AB>Reaction.state:NEW]
    AB{GameState}  --> |CREATED| AC
    AB  --> |PAUSED| AC
    AC{reaction is <br> game-emoji} --> |yes| AD
    AC --> |no| AK
    AD[[Remove reaction]] --> AF>Reaction.state:DELETED_STATUS]
    AB  --> |RUNNING| AG
    AG{reaction is <br> game-emoji} --> |yes| AH
    AG --> |no| AK
    AH{user is <br> game participant} --> |yes| AI>Reaction.state:REGISTERED]
    AH --> |no| AJ
    AJ[[Remove reation]] --> AL>Reaction.state:DELETED_PLAYER]
    AK>Reaction.state:SUPPORTER]
    AF --> AZ[End]
    AI --> AZ
    AL --> AZ
    AK --> AZ
