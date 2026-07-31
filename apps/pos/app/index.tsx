import { View, Text } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

export default function PosRoot() {
  return (
    <SafeAreaView className="flex-1 bg-white">
      <View className="flex-1 items-center justify-center">
        <Text className="text-3xl font-bold text-blue-700">SmartServe POS</Text>
        <Text className="text-gray-500 mt-2">Tablet point of sale — coming in step/07</Text>
      </View>
    </SafeAreaView>
  )
}
