
const fs = require('fs');
const path = require('path');

exports.handler = async function(event, context) {
    const filePath = path.resolve(__dirname, 'defect_data.json');

    try {
        let data = [];
        if (fs.existsSync(filePath)) {
            data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        }

        return {
            statusCode: 200,
            body: JSON.stringify(data)
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
