const { 
  Client, 
  GatewayIntentBits, 
  EmbedBuilder, 
  ActionRowBuilder, 
  StringSelectMenuBuilder, 
  StringSelectMenuOptionBuilder, 
  REST, 
  Routes, 
  SlashCommandBuilder 
} = require('discord.js');
const { joinVoiceChannel, getVoiceConnection } = require('@discordjs/voice');
const fs = require('fs');
const path = require('path');
const http = require('http');
const axios = require('axios');
const Papa = require('papaparse');

// ==========================================
// 1. Keep Alive 웹서버 구현 (http 모듈)
// ==========================================
const PORT = process.env.PORT || 8080;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Bot is running!');
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🌐 웹 서버가 포트 ${PORT}번에서 실행 중이야!`);
});

// ==========================================
// 2. 디스코드 클라이언트 설정
// ==========================================
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates
  ]
});

// 캐릭터 이미지 로드 (data/char_images.json 경로)
function loadCharImages() {
  const jsonPath = path.join(__dirname, 'data', 'char_images.json');
  
  if (fs.existsSync(jsonPath)) {
    try {
      const rawData = fs.readFileSync(jsonPath, 'utf-8');
      const data = JSON.parse(rawData);
      const result = {};
      for (const [k, v] of Object.entries(data)) {
        result[String(k).trim()] = String(v).trim();
      }
      return result;
    } catch (e) {
      console.log(`JSON 로드 중 오류 발생: ${e}`);
    }
  } else {
    console.log(`⚠️ 경로에 파일이 존재하지 않아: ${jsonPath}`);
  }
  return {};
}

// 구글 시트 데이터 로드 및 파싱
async function loadData() {
  const sheetId = '1C3ZpKCTQJXFwUBgZKZRdLOvGqDGlVijb';
  const gid = '2007866856';
  const csvUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=${gid}`;

  const columnNames = [
    '캐릭명', '진영', '특성', '스킬레벨', '포지션',
    'W-엔진', '4세트', '2세트', 'disc_4', 'disc_5',
    'disc_6', '유효부옵션', '핵심돌파', '주옵', '치명타', '기타'
  ];

  try {
    const response = await axios.get(csvUrl, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' },
      responseType: 'text'
    });

    const parsed = Papa.parse(response.data, { header: false });
    const rawData = parsed.data;
    console.log(`📊 [디버그] CSV 전체 행 수: ${rawData.length}`);

    const processedRows = [];
    const totalRows = rawData.length;

    for (let startIdx = 5; startIdx < totalRows; startIdx += 4) {
      const chunk = rawData.slice(startIdx, startIdx + 4);
      if (chunk.length < 4) continue;

      const lastRow = chunk[chunk.length - 1];
      const lastVal = lastRow ? lastRow[0] : null;

      if (!lastVal) continue;

      const charName = String(lastVal).trim();
      if (!charName || ['캐릭명', '캐릭터', 'nan', 'None', '-', '이름'].includes(charName)) {
        continue;
      }

      const rowData = {};

      columnNames.forEach((col, colIdx) => {
        const validVals = chunk
          .map(row => (row[colIdx] !== undefined && row[colIdx] !== null) ? String(row[colIdx]).trim() : '')
          .filter(v => v !== '' && !['nan', 'None', '-', 'NaN'].includes(v));

        if (['disc_4', 'disc_5', 'disc_6'].includes(col)) {
          rowData[col] = validVals.length > 0 ? validVals[0] : '-';
        } else if (['W-엔진', '기타', '유효부옵션'].includes(col)) {
          rowData[col] = validVals.length > 0 ? validVals.join('\n') : '-';
        } else {
          rowData[col] = validVals.length > 0 ? validVals[0] : '-';
        }
      });

      const mains = [rowData['disc_4'], rowData['disc_5'], rowData['disc_6']].filter(m => m !== '-');
      rowData['통합디스크주옵션'] = mains.length > 0 ? mains.join(' / ') : '-';
      rowData['캐릭명'] = charName;

      processedRows.push(rowData);
    }

    if (processedRows.length === 0) {
      console.log('⚠️ [디버그] 파싱된 데이터가 없어! 캐릭터 이름 위치나 행 구도를 다시 확인해 볼래?');
    } else {
      console.log(`✅ [디버그] 파싱 성공! 총 ${processedRows.length}명의 캐릭터가 정상 로드됐어!`);
    }

    return processedRows;
  } catch (e) {
    console.log(`❌ 구글 시트 로드 중 오류 발생: ${e}`);
    return [];
  }
}

// 세팅 Embed 생성
function createSettingEmbed(row) {
  const charName = String(row['캐릭명']).trim();
  const charImages = loadCharImages();
  const imageUrl = charImages[charName];

  const embed = new EmbedBuilder()
    .setTitle(`🎮 ${charName} 세팅 가이드`)
    .setColor(0x00ff00)
    .addFields(
      { name: '🏛️ 진영', value: row['진영'], inline: true },
      { name: '⚡ 특성', value: row['특성'], inline: true },
      { name: '🎯 포지션', value: row['포지션'], inline: true },
      { name: '🗡️ W-엔진', value: row['W-엔진'], inline: false },
      { name: '🔮 4세트', value: row['4세트'], inline: true },
      { name: '💎 2세트', value: row['2세트'], inline: true },
      { name: '📊 디스크 4 / 5 / 6번 주옵션', value: row['통합디스크주옵션'], inline: false },
      { name: '✨ 유효 부옵션', value: row['유효부옵션'], inline: true },
      { name: '💥 스킬 레벨', value: row['스킬레벨'], inline: true },
      { name: '🚀 핵심 돌파', value: row['핵심돌파'], inline: true },
      { name: '⚙️ 주요 옵션', value: row['주옵'], inline: true },
      { name: '🎯 치명타 정보', value: row['치명타'], inline: true }
    )
    .setFooter({ text: '젠존제 세팅 정보 봇' });

  if (imageUrl && (imageUrl.startsWith('http://') || imageUrl.startsWith('https://'))) {
    embed.setThumbnail(imageUrl);
  }

  if (row['기타'] && row['기타'] !== '-') {
    embed.addFields({ name: '📌 기타 팁', value: row['기타'], inline: false });
  }

  return { charName, embed };
}

// 슬래시 명령어 등록 정의
const commands = [
  new SlashCommandBuilder()
    .setName('목록')
    .setDescription('세팅 정보가 등록된 전체 캐릭터 목록을 확인해!'),
  new SlashCommandBuilder()
    .setName('세팅')
    .setDescription('젠존제 캐릭터 세팅 정보를 검색해!')
    .addStringOption(option =>
      option.setName('캐릭터')
        .setDescription('검색할 캐릭터 이름을 입력해줘 (선택 사항)')
        .setRequired(false)
    )
].map(command => command.toJSON());

// 봇 준비 이벤트
client.once('ready', async () => {
  console.log(`🤖 봇 로그인 성공: ${client.user.tag}`);
  client.user.setActivity('에이전트 관리 중');

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    await rest.put(
      Routes.applicationCommands(client.user.id),
      { body: commands }
    );
    console.log('✅ 슬래시 명령어 동기화 완료!');
  } catch (error) {
    console.error('❌ 슬래시 명령어 동기화 실패:', error);
  }
});

// 일반 텍스트 명령어 (!입장, !퇴장)
client.on('messageCreate', async message => {
  if (message.author.bot) return;

  if (message.content === '!입장') {
    const voiceChannel = message.member?.voice.channel;
    if (voiceChannel) {
      joinVoiceChannel({
        channelId: voiceChannel.id,
        guildId: message.guild.id,
        adapterCreator: message.guild.voiceAdapterCreator,
      });
      await message.channel.send(`🔊 **${voiceChannel.name}** 음성 채널에 들어왔어! \`!퇴장\` 명령어를 치기 전까지 계속 남아있을게~`);
    } else {
      await message.channel.send('❌ 먼저 음성 채널에 들어가 있어야 날 부를 수 있어!');
    }
  }

  if (message.content === '!퇴장') {
    const connection = getVoiceConnection(message.guild.id);
    if (connection) {
      connection.destroy();
      await message.channel.send('👋 음성 채널에서 나왔어!');
    } else {
      await message.channel.send('❌ 나 아직 어떤 음성 채널에도 들어가 있지 않아!');
    }
  }
});

// 슬래시 명령어 처리 및 드롭다운 Interaction 처리
client.on('interactionCreate', async interaction => {
  if (interaction.isChatInputCommand()) {
    const { commandName } = interaction;

    if (commandName === '목록') {
      await interaction.deferReply();
      const df = await loadData();

      if (!df || df.length === 0) {
        await interaction.editReply('❌ 등록된 캐릭터 데이터를 불러올 수 없어!');
        return;
      }

      const charList = [...new Set(df.map(row => row['캐릭명']))].sort();
      const textList = charList.map(name => `• ${name}`).join('\n');

      const embed = new EmbedBuilder()
        .setTitle('📜 등록된 캐릭터 목록')
        .setDescription(textList)
        .setColor(0x3498db)
        .setFooter({ text: `총 ${charList.length}명의 캐릭터가 등록되어 있어!` });

      await interaction.editReply({ embeds: [embed] });
    }

    if (commandName === '세팅') {
      const characterInput = interaction.options.getString('캐릭터');
      await interaction.deferReply({ ephemeral: !characterInput });

      try {
        const df = await loadData();

        if (!df || df.length === 0) {
          await interaction.editReply({ content: '❌ 캐릭터 데이터를 로드하지 못했어!', ephemeral: true });
          return;
        }

        if (characterInput) {
          const searchName = characterInput.replace(/\s+/g, '').toLowerCase();

          if (searchName === '배연우') {
            await interaction.editReply(`<@${interaction.user.id}> 너 배연우`);
            return;
          }

          if (searchName === '베리나') {
            const images = loadCharImages();
            const imgUrl = images['베리나'] || 'https://i.namu.wiki/i/eACVAos4WR6IB2Y1AlVn8qXnKlzxYWTsR6AULHvS9w-bbhphy1X4_iszgM8zdCRhSA0zfvvZpqNRIluNxNauxw.webp';
            await interaction.editReply(`<@${interaction.user.id}> 너 미래 남편\n${imgUrl}`);
            return;
          }

          const matched = df.filter(row =>
            String(row['캐릭명']).replace(/\s+/g, '').toLowerCase().includes(searchName)
          );

          if (matched.length === 0) {
            await interaction.editReply({ content: `❌ **${characterInput}** 캐릭터 정보를 찾을 수 없어!`, ephemeral: true });
            return;
          }

          const { charName, embed } = createSettingEmbed(matched[0]);
          await interaction.editReply({ content: `**${charName}** 세팅 정보를 가져왔어!`, embeds: [embed] });
        } else {
          const selectMenu = new StringSelectMenuBuilder()
            .setCustomId('select_category')
            .setPlaceholder('카테고리를 선택해 줘!')
            .addOptions(
              new StringSelectMenuOptionBuilder().setLabel('전체 보기').setDescription('모든 캐릭터 보기').setValue('전체'),
              new StringSelectMenuOptionBuilder().setLabel('진영별 보기').setDescription('진영으로 캐릭터 찾아보기').setValue('진영'),
              new StringSelectMenuOptionBuilder().setLabel('특성별 보기').setDescription('속성/특성으로 캐릭터 찾아보기').setValue('특성'),
              new StringSelectMenuOptionBuilder().setLabel('포지션별 보기').setDescription('포지션(역할군)으로 캐릭터 찾아보기').setValue('포지션')
            );

          const row = new ActionRowBuilder().addComponents(selectMenu);
          await interaction.editReply({ content: '원하는 카테고리를 아래 드롭다운에서 골라줘!', components: [row], ephemeral: true });
        }
      } catch (e) {
        await interaction.editReply({ content: `⚠️ 데이터를 불러오는 중 오류가 발생했어: ${e}`, ephemeral: true });
      }
    }
  }

  if (interaction.isStringSelectMenu()) {
    const df = await loadData();

    if (interaction.customId === 'select_category') {
      const selected = interaction.values[0];

      if (selected === '전체') {
        const charList = [...new Set(df.map(row => row['캐릭명']))].sort();
        const textList = charList.length > 0 ? charList.join(', ') : '등록된 캐릭터가 없어!';
        const embed = new EmbedBuilder().setTitle('📜 전체 캐릭터 목록').setDescription(textList).setColor(0x3498db);

        await interaction.update({ content: '검색 가능한 전체 캐릭터 목록이야!', embeds: [embed], components: [] });
      } else if (['진영', '특성', '포지션'].includes(selected)) {
        const uniqueVals = [...new Set(df.map(row => String(row[selected]).trim()))].filter(v => v && v !== '-');

        const selectMenu = new StringSelectMenuBuilder()
          .setCustomId(`select_subcategory_${selected}`)
          .setPlaceholder(`${selected} 선택...`);

        if (uniqueVals.length > 0) {
          selectMenu.addOptions(
            uniqueVals.slice(0, 25).map(val => new StringSelectMenuOptionBuilder().setLabel(val).setValue(val))
          );
        } else {
          selectMenu.addOptions(new StringSelectMenuOptionBuilder().setLabel('데이터 없음').setValue('none'));
        }

        const row = new ActionRowBuilder().addComponents(selectMenu);
        await interaction.update({ content: `원하는 **${selected}**을(를) 선택해 줘!`, components: [row] });
      }
    } else if (interaction.customId.startsWith('select_subcategory_')) {
      const categoryType = interaction.customId.replace('select_subcategory_', '');
      const selectedVal = interaction.values[0];

      if (selectedVal === 'none') {
        await interaction.reply({ content: '해당 카테고리에 데이터가 없어!', ephemeral: true });
        return;
      }

      const matched = df.filter(row => String(row[categoryType]).trim() === selectedVal);

      const selectMenu = new StringSelectMenuBuilder()
        .setCustomId('select_character')
        .setPlaceholder('캐릭터를 선택해 줘!')
        .addOptions(
          matched.slice(0, 25).map(row => {
            const name = String(row['캐릭명']).trim();
            return new StringSelectMenuOptionBuilder().setLabel(name).setValue(name);
          })
        );

      const row = new ActionRowBuilder().addComponents(selectMenu);
      await interaction.update({ content: `**[${selectedVal}]** 카테고리의 캐릭터를 선택해 줘!`, components: [row] });
    } else if (interaction.customId === 'select_character') {
      const selectedChar = interaction.values[0];
      const rowData = df.find(row => String(row['캐릭명']).trim() === selectedChar);

      if (rowData) {
        const { charName, embed } = createSettingEmbed(rowData);
        await interaction.update({ content: `**${charName}** 세팅 정보를 가져왔어!`, embeds: [embed], components: [] });
      }
    }
  }
});

client.login(process.env.DISCORD_TOKEN);
