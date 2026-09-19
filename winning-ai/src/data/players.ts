export interface Player {
    id: number;
    name: string;
    position: 'arq' | 'def' | 'vol' | 'del';
    team: string;
    points: number;
    statistics: {
        goals: number;
        assists: number;
        cleanSheets: number;
        yellowCards: number;
        redCards: number;
        minutesPlayed: number;
    };
}

export const players: Player[] = [
    {
        id: 1,
        name: 'Jugador 1',
        position: 'arq',
        team: 'Equipo A',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 2,
        name: 'Jugador 2',
        position: 'def',
        team: 'Equipo A',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 3,
        name: 'Jugador 3',
        position: 'def',
        team: 'Equipo B',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 4,
        name: 'Jugador 4',
        position: 'def',
        team: 'Equipo C',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 5,
        name: 'Jugador 5',
        position: 'vol',
        team: 'Equipo A',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 6,
        name: 'Jugador 6',
        position: 'vol',
        team: 'Equipo B',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 7,
        name: 'Jugador 7',
        position: 'vol',
        team: 'Equipo C',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 8,
        name: 'Jugador 8',
        position: 'del',
        team: 'Equipo A',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 9,
        name: 'Jugador 9',
        position: 'del',
        team: 'Equipo B',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
    {
        id: 10,
        name: 'Jugador 10',
        position: 'del',
        team: 'Equipo C',
        points: 0,
        statistics: {
            goals: 0,
            assists: 0,
            cleanSheets: 0,
            yellowCards: 0,
            redCards: 0,
            minutesPlayed: 0,
        },
    },
];