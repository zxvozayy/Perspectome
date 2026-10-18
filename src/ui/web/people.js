// Perspectome — a small library of people, drawn as single-colour silhouettes.
// Each figure stands with its feet on y = 0, centred on x = 0; an adult is about 100 units tall.
// The page fills them through CSS (fill on the enclosing <g>), so one shape serves every theme.
window.PTPeople = (() => {
  const C = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}"/>`;
  const R = (x, y, w, h, r = 0, a = 0, cx = x, cy = y) =>
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}"${a ? ` transform="rotate(${a} ${cx} ${cy})"` : ''}/>`;
  const P = d => `<path d="${d}"/>`;
  const legs = (w, gap, top, shoes = 0) =>
    R(-gap / 2 - w, top, w, -top, w / 4) + R(gap / 2, top, w, -top, w / 4) +
    (shoes ? R(-gap / 2 - w - 1.5, -shoes, w + 3, shoes, shoes / 2) + R(gap / 2 - 1.5, -shoes, w + 3, shoes, shoes / 2) : '');

  const TYPES = {
    // man in a suit, briefcase in hand
    business: { w: 36, svg:
      C(0, -89, 8.5) +
      P('M-15-72Q-15-80-8-80H8Q15-80 15-72L13-44H-13Z') +
      R(-19, -77, 6, 33, 3, 6, -16, -77) + R(13, -77, 6, 31, 3, -4, 16, -77) +
      R(9, -41, 18, 13, 2) + P('M14-41v-3.5a1.5 1.5 0 0 1 1.5-1.5h5a1.5 1.5 0 0 1 1.5 1.5V-41h-2v-3h-4v3z') +
      legs(9.5, 3, -46, 2.6) },
    // woman in a jacket and pencil skirt, hair in a bun, bag on the shoulder
    businesswoman: { w: 32, svg:
      C(5.6, -95.5, 4.4) + C(0, -89, 8) +
      P('M-12-72Q-12-80-6-80H6Q12-80 12-72L11-48H-11Z') + P('M-11-48H11L10-22H-10Z') +
      R(-16, -77, 5, 30, 2.5, 5, -13.5, -77) + R(11, -77, 5, 30, 2.5, -5, 13.5, -77) +
      R(12, -54, 11, 10, 2.5) + P('M13.5-54c0-9 8-9 8 0h-1.8c0-6.4-4.4-6.4-4.4 0z') +
      legs(5.2, 3, -23, 2.2) },
    // older man in a flat cap, leaning on a cane
    elder: { w: 38, svg:
      `<g transform="rotate(9 0 -45)">` +
        P('M-7-89a8.6 7.6 0 0 1 17.2 0l5.5 1.2v2.3h-22.7z') + C(1.6, -86, 8) +
        P('M-14-70Q-14-78-7-78H7Q14-78 14-70L12-44H-12Z') +
        R(-18, -75, 6, 30, 3, 4, -15, -75) + R(10, -75, 6, 28, 3, -22, 13, -75) +
      '</g>' +
      R(21.5, -45, 2.8, 45, 1.2) + R(17, -47, 9, 3, 1.5) +
      legs(9, 3, -46, 2.4) },
    // older woman in a headscarf and long skirt, a bag in her hand
    elderwoman: { w: 38, svg:
      `<g transform="rotate(5 0 -40)">` +
        P('M0-99c-7.5 0-10.5 5.5-10.5 11.5 0 4.5 1.8 7.6 3.8 9.6l-7 4.4h27.4l-7-4.4c2-2 3.8-5.1 3.8-9.6 0-6-3-11.5-10.5-11.5z') +
        P('M-13-74Q-13-78-8-78H8Q13-78 13-74L15-40H-15Z') +
        R(-17, -75, 5.5, 30, 2.7, 8, -14, -75) + R(11, -75, 5.5, 28, 2.7, -6, 13.5, -75) +
        R(12, -50, 11, 12, 2.5) +
      '</g>' +
      P('M-15.5-41H15.5L17.5-7H-17.5Z') + legs(5, 3, -8, 2.2) },
    // child with a backpack
    child: { w: 24, svg:
      C(0, -53, 7.6) +
      R(-13.5, -44, 6.5, 17, 2.8) +
      P('M-9-38Q-9-44-4-44H4Q9-44 9-38L8-24H-8Z') +
      R(-11.5, -43, 4, 17, 2, 8, -9.5, -43) + R(7.5, -43, 4, 17, 2, -8, 9.5, -43) +
      legs(6, 2.4, -25, 2) },
    // young girl in a dress, pigtails
    girl: { w: 24, svg:
      C(-7.5, -55, 3.2) + C(7.5, -55, 3.2) + C(0, -53, 7.4) +
      P('M-6-44H6L12-20H-12Z') +
      R(-10.5, -43, 3.8, 15, 1.9, 14, -8.5, -43) + R(6.7, -43, 3.8, 15, 1.9, -14, 8.5, -43) +
      legs(4.2, 2.4, -21, 2) },
    // student in a hoodie with a backpack
    student: { w: 36, svg:
      C(-1.4, -87.6, 10.6) + C(0, -89, 8.5) +
      R(-20, -76, 8, 27, 3.2) +
      P('M-14-70Q-14-79-7-79H7Q14-79 14-70L13-42H-13Z') +
      R(-17, -75, 6, 32, 3, 4, -14, -75) + R(11, -75, 6, 32, 3, -4, 14, -75) +
      legs(9.5, 3, -44, 3.4) },
    // woman with long hair in an A-line dress
    longhair: { w: 34, svg:
      P('M-9.5-88c0-8.4 4.2-12.6 9.5-12.6s9.5 4.2 9.5 12.6v15c0 3-2 4.2-4.2 4.2H-5.3c-2.2 0-4.2-1.2-4.2-4.2z') + C(0, -89, 7.8) +
      P('M-10-72Q-10-79-5-79H5Q10-79 10-72L17-32H-17Z') +
      R(-15, -77, 4.8, 30, 2.4, 10, -12, -77) + R(10, -77, 4.8, 30, 2.4, -10, 12, -77) +
      legs(5, 4, -33, 2.2) },
    // man on the phone
    phone: { w: 36, svg:
      C(0, -89, 8.5) +
      P('M-14-71Q-14-80-7-80H7Q14-80 14-71L12-44H-12Z') +
      R(-18, -77, 6, 33, 3, 5, -15, -77) + R(11, -78, 6, 17, 3, -28, 14, -78) +
      P('M24.5-64.3L19.6-61.7L6.6-86.7L11.5-89.3Z') + R(6.5, -96, 4.2, 10, 1.4) +
      legs(9.5, 3, -46, 2.6) },
    // worker in a hard hat with a toolbox
    worker: { w: 40, svg:
      P('M-10.5-92.5a10.5 9.5 0 0 1 21 0h3.4v2.8h-27.8v-2.8z') + C(0, -88, 8) +
      P('M-16-70Q-16-79-8-79H8Q16-79 16-70L14-44H-14Z') +
      R(-21, -76, 7, 32, 3.5, 6, -17, -76) + R(14, -76, 7, 30, 3.5, -6, 17, -76) +
      R(12, -38, 16, 10, 2) + R(17, -42, 6, 4.5, 1.5) +
      legs(10.5, 3, -46, 4) },
    // man in a coat and hat (fedora)
    coat: { w: 36, svg:
      P('M-13-95h26v2.6H-13z') + P('M-8-95q0-8 8-8t8 8z') + C(0, -88, 8.2) +
      P('M-14-71Q-14-80-7-80H7Q14-80 14-71L16-30H-16Z') +
      R(-19, -77, 6, 36, 3, 5, -16, -77) + R(13, -77, 6, 36, 3, -5, 16, -77) +
      legs(8.5, 3.5, -31, 2.6) },
    // mother holding her child's hand
    mother: { w: 52, svg:
      P('M-9.5-88c0-8.4 4.2-12.6 9.5-12.6s9.5 4.2 9.5 12.6v15c0 3-2 4.2-4.2 4.2H-5.3c-2.2 0-4.2-1.2-4.2-4.2z') + C(0, -89, 7.8) +
      P('M-10-72Q-10-79-5-79H5Q10-79 10-72L15-30H-15Z') +
      R(-15, -77, 4.8, 30, 2.4, 10, -12, -77) + R(10, -77, 4.8, 32, 2.4, -32, 12, -77) +
      legs(5, 4, -31, 2.2) +
      `<g transform="translate(29 0)">` + C(0, -52, 7.2) +
        P('M-8.5-37Q-8.5-43-4-43H4Q8.5-43 8.5-37L7.5-24H-7.5Z') +
        R(-10, -42, 4, 15, 2, 40, -8, -42) + R(6.5, -42, 4, 16, 2, -8, 8.5, -42) +
        legs(5.6, 2.4, -25, 2) + '</g>' },
  };
  const NAMES = Object.keys(TYPES);
  // A group of people where nobody repeats until everyone has had a turn.
  function cast(n, rand, pool = NAMES) {
    const out = [];
    let bag = [];
    for (let i = 0; i < n; i++) {
      if (!bag.length) bag = pool.slice().sort(() => rand() - .5);
      out.push(bag.pop());
    }
    return out;
  }
  return { TYPES, NAMES, cast };
})();
