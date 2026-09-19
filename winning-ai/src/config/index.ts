import { Config } from '../types';

const config: Config = {
    sofascoreApiUrl: 'https://api.sofascore.com/',
    scoring: {
        pointsPerGoal: 4,
        pointsPerAssist: 3,
        pointsPerCleanSheet: 2,
        pointsPerYellowCard: -1,
        pointsPerRedCard: -3,
        // Add more scoring parameters as needed
    },
    teamFormation: {
        playersPerTeam: 10,
        flexOptions: 3,
        formation: {
            goalkeeper: 1,
            defenders: 3,
            midfielders: 3,
            forwards: 3,
        },
    },
};

export default config;