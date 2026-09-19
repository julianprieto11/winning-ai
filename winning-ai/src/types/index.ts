export interface Player {
    id: number;
    name: string;
    position: 'goalkeeper' | 'defender' | 'midfielder' | 'forward';
    team: string;
    points: number;
    statistics: {
        goals: number;
        assists: number;
        cleanSheets: number;
        yellowCards: number;
        redCards: number;
    };
}

export interface Team {
    name: string;
    players: Player[];
}

export interface Match {
    id: number;
    date: string;
    homeTeam: string;
    awayTeam: string;
    result: {
        homeScore: number;
        awayScore: number;
    };
}

export interface Scoring {
    pointsPerGoal: number;
    pointsPerAssist: number;
    pointsPerCleanSheet: number;
    pointsPerYellowCard: number;
    pointsPerRedCard: number;
}