
const fs = require('fs');
const path = require('path');

exports.handler = async function(event, context) {
    const data = JSON.parse(event.body);
    const filePath = path.resolve(__dirname, 'defect_data.json');

    try {
        let existingData = [];
        if (fs.existsSync(filePath)) {
            existingData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        }

        const dateIndex = existingData.findIndex(item => item.date === data.date);
        if (dateIndex !== -1) {
            existingData[dateIndex].defects.push(...data.defects);
        } else {
            existingData.push(data);
        }

        fs.writeFileSync(filePath, JSON.stringify(existingData, null, 2));
        return {
            statusCode: 200,
            body: JSON.stringify({ message: 'Data saved successfully' })
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
