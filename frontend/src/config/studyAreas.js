import { rectangleBoundsToPolygon } from '../utils/geo'

const INDUS_BOUNDS = [66.5, 23.5, 68.5, 24.8]
const ABU_DHABI_BOUNDS = [54.32, 24.40, 54.52, 24.55]

export const STUDY_AREAS = [
  {
    id: 'indus_delta',
    name: 'Indus Delta',
    country: 'Pakistan',
    description: 'Temporary study extent used for workflow setup and preview.',
    boundaryType: 'provisional_bounding_rectangle',
    defaultStartDate: '2020-01-01',
    defaultEndDate: '2020-04-01',
    map: {
      center: [24.15, 67.5],
      zoom: 9,
    },
    geometry: rectangleBoundsToPolygon(INDUS_BOUNDS),
  },
  {
    id: 'abu_dhabi',
    name: 'Abu Dhabi',
    country: 'United Arab Emirates',
    description: 'Verified project study extent (54.32–54.52°E, 24.40–24.55°N).',
    boundaryType: 'verified_project_study_extent',
    defaultStartDate: '2019-01-01',
    defaultEndDate: '2021-12-31',
    map: {
      center: [24.475, 54.42],
      zoom: 12,
    },
    geometry: rectangleBoundsToPolygon(ABU_DHABI_BOUNDS),
  },
]

export const STUDY_AREAS_BY_ID = Object.fromEntries(STUDY_AREAS.map((area) => [area.id, area]))
export const DEFAULT_STUDY_AREA_ID = 'indus_delta'
