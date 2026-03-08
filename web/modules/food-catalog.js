const FOOD_MEDIA_BASE_URL = '/web/assets/food-covers';

const SHOP_GROUP_COVER_FILE = {
  unimall17: 'group-unimall17.svg',
  bh1: 'group-bh1.svg',
  bh2to6: 'group-bh2to6.svg',
  block41: 'group-block41.svg',
  block34: 'group-block34.svg',
  campus: 'group-campus.svg',
};

const FALLBACK_COVER_URL = `${FOOD_MEDIA_BASE_URL}/fallback.svg`;

const SHOP_REMOTE_COVER_BY_ID = {
  dominos: 'https://www.dominos.co.in/theme2/front/assets/banner2.webp',
  'wow-momo': 'https://marinamallchennai.com/wp-content/uploads/2020/08/rsz_elv02242-min.jpg',
  'chicago-pizza': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTBZ3sJ3rGxFwTen7xou80brkNAi2U3v4yN5Q&s',
  ccd: 'https://www.shutterstock.com/image-photo/mumbai-india-feb-23-cafe-600nw-2605028205.jpg',
  'andhra-food-house': 'https://lpubeyondclasses.weebly.com/uploads/5/9/7/7/59774945/1234924.jpg?250',
  'ab-juice-bar-bh1': 'https://happenings.lpu.in/wp-content/uploads/2018/02/7.2-1.jpg',
  'telugu-vantillu': 'https://b.zmtcdn.com/data/pictures/4/20876424/72e4680b9c9a66c3d157c1ceac1e5ceb.jpg',
  'campus-fusion-bh1': 'https://b.zmtcdn.com/data/pictures/chains/7/20402557/7c9fe2b6a8ae9d14736d68d1f11e18be_featured_v2.jpg',
  'havmor-ice-cream': 'https://content.jdmagicbox.com/v2/comp/delhi/l6/011pxx11.xx11.221228184909.u2l6/catalogue/-1qb99pzzka.jpg',
  'nk-food-court-bh2-6': 'https://i.pinimg.com/736x/42/7e/a2/427ea2b8d28fbaf5efc1f6f7db47e25a.jpg',
  'pizza-express': 'https://pizzaexpress.in/wp-content/uploads/2025/02/Lulu2-1024x683.jpg',
  'juice-world': 'https://b.zmtcdn.com/data/pictures/9/19235239/b4e9bc5386c4242cc71516a02664d38a.jpg?fit=around%7C960:500&crop=960:500;*,*',
  'chinese-eatery': 'https://dynamic-media-cdn.tripadvisor.com/media/photo-o/1a/b0/43/c4/traditional-chinese-restaurant.jpg?w=1200&h=1200&s=1',
  'nand-juice-bh2-6': 'https://content.jdmagicbox.com/v2/comp/phagwara/u2/9999p1824.1824.251108083345.v2u2/catalogue/nand-juice-corner-phagwara-juice-centres-zw6zkfkvyn.jpg',
  'campus-fusion-bh2-6': 'https://b.zmtcdn.com/data/pictures/chains/7/20402557/7c9fe2b6a8ae9d14736d68d1f11e18be_featured_v2.jpg',
  'kannu-ki-chai': 'https://kannukichai.com/wp-content/uploads/2024/01/2023.jpg',
  yippee: 'https://www.retail4growth.com/public/uploads/editor/2024-07-10/1720614018.jpeg',
  'kitchen-ette-block41': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSmbgumgEId2NhiLJru_xhGeGI8tU1PxzQLfg&s',
  'ab-juice-bar-block41': 'https://content.jdmagicbox.com/v2/comp/undefined/w3/0141px141.x141.230203182338.v9w3/catalogue/ab-juice-club-mansarovar-jaipur-juice-centres-gr4f661o1u.jpg',
  'basant-ice-cream-corner': 'https://content.jdmagicbox.com/comp/ludhiana/y3/0161px161.x161.120521093214.l4y3/catalogue/basant-ice-cream-ferozepur-road-ludhiana-ice-cream-distributors-gw5p0o36b2.jpg',
  'northern-delights': 'https://static.where-e.com/India/Uttar_Pradesh_State/Northern-Delights_8fdc73f2560fa6ab3e05f456a769dd54.jpg',
  'bengali-bawarchi': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSKKktniVK5RYKu_34CySDu6wACHGex2XAq0g&s',
  'tandoor-hub': 'https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,w_366/RX_THUMBNAIL/IMAGES/VENDOR/2024/10/17/0335aa92-1e2e-45d5-8f57-b3fe9dcc9482_410561.jpg',
  'nand-juice-block34': 'https://content.jdmagicbox.com/v2/comp/phagwara/u2/9999p1824.1824.251108083345.v2u2/catalogue/nand-juice-corner-phagwara-juice-centres-zw6zkfkvyn.jpg',
  'oven-express': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTyxtuHgUZkBkQbEe1FqMNEM0kapS4Lqgwz6g&s',
};

function resolveGroupCover(groupKey = '') {
  const normalized = String(groupKey || '').trim();
  const filename = SHOP_GROUP_COVER_FILE[normalized];
  if (!filename) {
    return FALLBACK_COVER_URL;
  }
  return `${FOOD_MEDIA_BASE_URL}/${filename}`;
}

const SHOP_DIRECTORY_BASE = [
  { id: 'dominos', name: "Domino's Pizza", block: 'UniMall - Block 17', group: 'unimall17' },
  { id: 'wow-momo', name: 'Wow! Momo', block: 'UniMall - Block 17', group: 'unimall17' },
  { id: 'chicago-pizza', name: 'Chicago Pizza', block: 'UniMall - Block 17', group: 'unimall17' },
  { id: 'ccd', name: 'Cafe Coffee Day', block: 'UniMall - Block 17', group: 'unimall17' },
  { id: 'andhra-food-house', name: 'Andhra Food House', block: 'BH-1', group: 'bh1' },
  { id: 'ab-juice-bar-bh1', name: 'AB Juice Bar', block: 'BH-1', group: 'bh1' },
  { id: 'telugu-vantillu', name: 'Telugu Vantillu', block: 'BH-1', group: 'bh1' },
  { id: 'campus-fusion-bh1', name: 'Campus Fusion', block: 'BH-1', group: 'bh1' },
  { id: 'havmor-ice-cream', name: 'Havmor Ice Cream', block: 'BH-1', group: 'bh1' },
  { id: 'nk-food-court-bh2-6', name: 'NK Food Court', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'pizza-express', name: 'Pizza Express', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'juice-world', name: 'Juice World', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'chinese-eatery', name: 'Chinese Eatery', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'nand-juice-bh2-6', name: 'Nand Juice', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'campus-fusion-bh2-6', name: 'Campus Fusion', block: 'BH-2 to BH-6', group: 'bh2to6' },
  { id: 'kannu-ki-chai', name: 'Kannu Ki Chai', block: 'Block-41', group: 'block41' },
  { id: 'yippee', name: 'Yippee', block: 'Block-41', group: 'block41' },
  { id: 'kitchen-ette-block41', name: 'Kitchen Ette', block: 'Block-41', group: 'block41' },
  { id: 'ab-juice-bar-block41', name: 'AB Juice Bar', block: 'Block-41', group: 'block41' },
  { id: 'basant-ice-cream-corner', name: 'Basant Ice Cream Corner', block: 'Block-41', group: 'block41' },
  { id: 'northern-delights', name: 'Northern Delights', block: 'Block-34', group: 'block34' },
  { id: 'bengali-bawarchi', name: 'Bengali Bawarchi', block: 'Block-34', group: 'block34' },
  { id: 'tandoor-hub', name: 'Tandoor Hub', block: 'Block-34', group: 'block34' },
  { id: 'nand-juice-block34', name: 'Nand Juice', block: 'Block-34', group: 'block34' },
  { id: 'oven-express', name: 'Oven Express', block: 'Campus-wide', group: 'campus' },
];

const SLOT_FALLBACK = Array.from({ length: 11 }, (_, index) => {
  const startHour = 10 + index;
  const endHour = startHour + 1;
  return {
    id: index + 1,
    label: `${String(startHour).padStart(2, '0')}:00 - ${String(endHour).padStart(2, '0')}:00`,
    start_time: `${String(startHour).padStart(2, '0')}:00:00`,
    end_time: `${String(endHour).padStart(2, '0')}:00:00`,
    max_orders: 250,
  };
});

const SHOP_DIRECTORY = SHOP_DIRECTORY_BASE.map((shop) => {
  const fallbackCover = resolveGroupCover(shop.group);
  return {
    ...shop,
    cover: SHOP_REMOTE_COVER_BY_ID[shop.id] || fallbackCover,
    fallbackCover,
  };
});

export const foodCatalog = {
  fallbackCoverUrl: FALLBACK_COVER_URL,
  popularSpotIds: ['oven-express', 'kitchen-ette-block41', 'nk-food-court-bh2-6'],
  shopGroups: [
    { key: 'popular', title: 'Popular Spots', subtitle: 'Most loved by students right now' },
    { key: 'unimall17', title: 'UniMall - Block 17', subtitle: 'Branded chains' },
    { key: 'bh1', title: 'BH-1 Food Kiosk Area', subtitle: 'Quick meals and snacks' },
    { key: 'bh2to6', title: 'BH-2 to BH-6 Kiosk Cluster', subtitle: 'High variety cluster' },
    { key: 'block41', title: 'Block-41 Food Court Zone', subtitle: 'Tea + snack hub' },
    { key: 'block34', title: 'Block-34 Kiosk Area', subtitle: 'Hidden popular picks' },
  ],
  slotFallback: SLOT_FALLBACK,
  aiQuickCravings: [
    'Spicy snacks under INR 150',
    'Healthy juice and light meal',
    'Coffee + dessert combo',
    'North Indian full meal',
    'Fast pizza pickup',
  ],
  deliveryPoints: [
    ['01', 'LIM'], ['02', 'Campus Cafe'], ['03', 'Auditorium'], ['04', 'LIT Engineering'],
    ['05', 'LIT Pharmacy'], ['06', 'LIT Architecture'], ['07', 'LIT Pharmacy'], ['08', 'Shri Baldev Raj Mittal Auditorium'],
    ['09', 'Girls Hostel 1'], ['10', 'Girls Hostel 2'], ['11', 'Girls Hostel 3'], ['12', 'Girls Hostel 4'],
    ['13', 'LIT Polytechnic'], ['14', 'Business Block'], ['15', 'Lovely Mall'], ['16', 'Hotel Mgt'],
    ['17', 'Mall - II'], ['18', 'Education'], ['19', 'Auditorium'], ['20', 'LSB'],
    ['21', 'Girl Hostel 5'], ['22', 'Girl Hostel 6'], ['23', 'Auditorium'], ['24', 'Auditorium'],
    ['25', 'Engineering'], ['26', 'Engineering'], ['27', 'Engineering'], ['28', 'Engineering'],
    ['29', 'Engineering'], ['30', 'Chancellor Office'], ['31', 'Administrative Block'], ['32', 'Administrative Block'],
    ['33', 'Engineering'], ['34', 'Engineering'], ['35', 'Engineering'], ['36', 'Engineering'],
    ['37', 'Engineering'], ['38', 'Engineering'], ['39', 'STP'], ['40', 'Store'],
    ['41', 'Staff Residence'], ['42', 'Staff Residence'], ['43', 'Boys Hostel 1'], ['45', 'Boys Hostel 2'],
    ['46', 'Boys Hostel 3'], ['47', 'Boys Hostel 4'], ['51', 'Boys Hostel 5'], ['52', 'Boys Hostel 6'],
    ['53', 'Academic Block 1'], ['54', 'Academic Block 2'], ['55', 'Academic Block 3'], ['71', 'Boys Studios 8'],
    ['72', 'Boys Studios 9'], ['73', 'Boys Studios 10'],
  ],
  shopDirectory: SHOP_DIRECTORY,
};
